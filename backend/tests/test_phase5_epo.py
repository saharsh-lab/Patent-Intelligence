"""Phase 5 (no database): publication numbers, CQL, OPS parsing, EPO client over mock HTTP."""

import json
from datetime import date

import httpx
import pytest

from app.core.errors import ConfigurationError, ExternalServiceError
from app.patents.base import PatentQuery
from app.patents.demo import DemoPatentSource
from app.patents.epo import (
    EpoOpsSource,
    build_cql,
    parse_biblio_response,
    parse_fulltext,
    parse_search_response,
)
from app.patents.numbers import parse_publication_number
from tests.helpers import FIXTURES

EPO = FIXTURES / "epo"


def load(name: str) -> dict:
    return json.loads((EPO / name).read_text())


# ------------------------------------------------------------------ numbers


@pytest.mark.parametrize(
    ("raw", "normalized", "docdb"),
    [
        ("EP 1 234 567 A1", "EP1234567A1", "EP.1234567.A1"),
        ("ep1234567a1", "EP1234567A1", "EP.1234567.A1"),
        ("US 10,123,456 B2", "US10123456B2", "US.10123456.B2"),
        ("WO 2020/123456 A1", "WO2020123456A1", "WO.2020123456.A1"),
        ("EP-1234567", "EP1234567", "EP.1234567"),
        ("EP.1234567.B1", "EP1234567B1", "EP.1234567.B1"),
    ],
)
def test_publication_number_normalisation(raw, normalized, docdb):
    number = parse_publication_number(raw)
    assert number.normalized == normalized
    assert number.docdb == docdb


@pytest.mark.parametrize("raw", ["", "1234567", "patent number", "E1234"])
def test_invalid_publication_numbers(raw):
    with pytest.raises(ValueError):
        parse_publication_number(raw)


# ------------------------------------------------------------------ CQL


def test_build_cql_combines_fields():
    query = PatentQuery(
        keywords='battery "thermal" runaway',
        cpc=["H01M 10/48"],
        applicant="Example Energy",
        date_from=date(2015, 1, 1),
        date_to=date(2024, 12, 31),
    )
    assert build_cql(query) == (
        'ta all "battery  thermal  runaway" and cpc=H01M10/48 and pa all "Example Energy"'
        ' and pd within "20150101 20241231"'
    )


def test_build_cql_single_date_bound_and_empty_query():
    assert build_cql(PatentQuery(keywords="coil", date_from=date(2020, 1, 1))) == (
        'ta all "coil" and pd>=20200101'
    )
    with pytest.raises(ValueError):
        build_cql(PatentQuery(keywords='  "  '))


def test_build_cql_office_filter_ignores_invalid_codes():
    query = PatentQuery(keywords="coil", countries=["ep", "WO", "x) or (1"])
    assert build_cql(query) == 'ta all "coil" and (pn=EP or pn=WO)'
    with pytest.raises(ValueError):  # an office alone is not a search
        build_cql(PatentQuery(countries=["EP"]))


# ------------------------------------------------------------------ parsing


def test_parse_search_response():
    total, records = parse_search_response(load("search_biblio.json"))
    assert total == 2
    first, second = records
    assert first.publication_number == "EP1234567A1"
    assert first.title == "Battery thermal management with core temperature estimation"  # English
    assert first.applicants == ["EXAMPLE ENERGY CORP"]  # epodoc form, country tag removed
    assert first.inventors == ["DOE JANE", "ROE RICHARD"]
    assert first.cpc_codes == ["H01M10/486", "H01M10/613"]
    assert first.publication_date == date(2021, 3, 4)
    assert first.filing_date == date(2019, 9, 12)
    assert first.priority_date == date(2018, 9, 15)
    assert first.family_id == "70001111"
    assert first.abstract.startswith("A controller estimates")
    assert first.url.endswith("pn%3DEP1234567A1")
    # second document: single objects instead of lists, no abstract, original-format names
    assert second.publication_number == "WO2020123456A1"
    assert second.applicants == ["Sample Batteries GmbH"]
    assert second.abstract is None


def test_parse_biblio_and_fulltext():
    [record] = parse_biblio_response(load("biblio_EP1234567A1.json"))
    assert record.abstract == (
        "A controller estimates the core temperature of each battery cell. "
        "Coolant flow is increased when a limit is exceeded."
    )
    claims = parse_fulltext(load("claims_EP1234567A1.json"), "claims")
    assert claims.startswith("1. A battery thermal management system")  # English chosen
    assert "\n\n2. The system of claim 1" in claims
    description = parse_fulltext(load("description_EP1234567A1.json"), "description")
    assert description.split("\n\n")[1].startswith("[0002]")


def test_parsers_tolerate_empty_responses():
    assert parse_search_response({}) == (0, [])
    assert parse_biblio_response({}) == []
    assert parse_fulltext({}, "claims") is None


# ------------------------------------------------------------------ client over mock HTTP


class FakeOps:
    """A tiny stand-in for ops.epo.org used through httpx.MockTransport."""

    def __init__(self):
        self.calls: list[httpx.Request] = []
        self.token_requests = 0
        self.overrides: dict[str, httpx.Response] = {}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        path = request.url.path
        for fragment, response in self.overrides.items():
            if fragment in path:
                return response
        if path.endswith("/auth/accesstoken"):
            self.token_requests += 1
            return httpx.Response(200, json={"access_token": "tok-1", "expires_in": "1199"})
        assert request.headers["Authorization"] == "Bearer tok-1"
        if path.endswith("/search/biblio"):
            return httpx.Response(200, json=load("search_biblio.json"))
        if path.endswith("/EP.1234567.A1/biblio"):
            return httpx.Response(200, json=load("biblio_EP1234567A1.json"))
        if path.endswith("/EP.1234567.A1/claims"):
            return httpx.Response(200, json=load("claims_EP1234567A1.json"))
        return httpx.Response(404, text="<error>not found</error>")


@pytest.fixture
def ops():
    fake = FakeOps()
    client = EpoOpsSource("key", "secret", http=httpx.Client(transport=httpx.MockTransport(fake)))
    return fake, client


def test_search_sends_cql_and_reuses_token(ops):
    fake, client = ops
    page = client.search(PatentQuery(keywords="battery thermal", limit=10))
    client.search(PatentQuery(keywords="battery thermal", limit=10))
    assert [r.publication_number for r in page.results] == ["EP1234567A1", "WO2020123456A1"]
    assert page.query_string == 'ta all "battery thermal"'
    search = [c for c in fake.calls if c.url.path.endswith("/search/biblio")][0]
    assert search.url.params["q"] == 'ta all "battery thermal"'
    assert search.url.params["Range"] == "1-10"
    assert fake.token_requests == 1  # token cached between calls


def test_no_results_404_is_empty_page(ops):
    fake, client = ops
    fake.overrides["/search/biblio"] = httpx.Response(404, text="<error>no results</error>")
    page = client.search(PatentQuery(keywords="nothing matches this"))
    assert (page.total, page.results) == (0, [])


def test_fair_use_rejection_is_explained(ops):
    fake, client = ops
    fake.overrides["/search/biblio"] = httpx.Response(
        403, headers={"X-Rejection-Reason": "IndividualQuotaPerHour"}, text="<error/>"
    )
    with pytest.raises(ExternalServiceError, match="IndividualQuotaPerHour"):
        client.search(PatentQuery(keywords="battery"))


def test_bad_credentials_are_a_configuration_error(ops):
    fake, client = ops
    fake.overrides["/auth/accesstoken"] = httpx.Response(401, text="invalid client")
    with pytest.raises(ConfigurationError):
        client.search(PatentQuery(keywords="battery"))


def test_get_details_combines_biblio_claims_and_missing_description(ops):
    _, client = ops
    record = client.get_details("EP 1234567 A1")
    assert record.title.startswith("Battery thermal")
    assert record.has_claims and record.claims_text.startswith("1. A battery")
    assert record.has_description is False and record.description_text is None


def test_missing_credentials_rejected():
    with pytest.raises(ConfigurationError):
        EpoOpsSource("", "")


# ------------------------------------------------------------------ demo source


def test_demo_source_is_clearly_synthetic_and_filterable():
    demo = DemoPatentSource()
    page = demo.search(PatentQuery(keywords="battery coolant temperature"))
    assert page.results and all(r.publication_number.startswith("XX") for r in page.results)
    assert all(r.claims_text is None for r in page.results)  # search = biblio only
    assert demo.search(PatentQuery(keywords="battery", cpc=["H02J"])).results == []
    details = demo.get_details(page.results[0].publication_number)
    assert details.claims_text and "SYNTHETIC" in details.description_text


# ------------------------------------------------------------------ real recorded responses


@pytest.mark.skipif(
    not (EPO / "recorded_search.json").exists(),
    reason="No recorded EPO responses yet (run scripts/record_epo_fixtures.py with credentials)",
)
def test_parser_handles_recorded_real_responses():
    total, records = parse_search_response(load("recorded_search.json"))
    assert total > 0 and records
    assert all(r.publication_number and r.title for r in records)
    if (EPO / "recorded_biblio.json").exists():
        assert parse_biblio_response(load("recorded_biblio.json"))
    if (EPO / "recorded_claims.json").exists():
        assert parse_fulltext(load("recorded_claims.json"), "claims")
