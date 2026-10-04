"""European Patent Office — Open Patent Services (OPS) v3.2 client.

How OPS works (https://developers.epo.org):
1. Authenticate: POST /auth/accesstoken with your consumer key + secret (HTTP Basic)
   → a bearer token valid for ~20 minutes. We cache and refresh it automatically.
2. Search:  GET /rest-services/published-data/search/biblio?q=<CQL>&Range=1-25
   CQL is EPO's query language, e.g.  ta all "battery thermal" and pd within "2015 2024"
3. Details: GET /rest-services/published-data/publication/docdb/EP.1234567.A1/biblio
   (and .../claims, .../description)
   Claims/description ("full text") exist only for some offices (EP, WO, and a few others).

Quirks handled here:
- Responses are XML converted to JSON: text lives under "$", attributes under "@name",
  and a list with one element arrives as a single object (see `_as_list`).
- A search with no hits returns HTTP 404, not an empty list.
- Fair-use throttling: OPS reports load in the X-Throttling-Control header and
  answers 403 (with an X-Rejection-Reason header, e.g. "IndividualQuotaPerHour")
  when a quota is exceeded.
- Verified against the live service so far: only the 403 fair-use rejection. The
  JSON shapes below follow the OPS v3.2 documentation; tests use hand-made responses
  until scripts/record_epo_fixtures.py records real ones (needs EPO credentials).

Responses are cached by the service layer, so repeated searches cost no quota.
"""

import logging
import re
import threading
import time
from datetime import date
from typing import Any

import httpx

from app.core.errors import ConfigurationError, ExternalServiceError
from app.patents.base import PatentQuery, PatentRecord, PatentSearchPage, PatentSource
from app.patents.numbers import parse_publication_number

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://ops.epo.org/3.2"
MAX_RANGE = 100  # OPS returns at most 100 results per request


def _as_list(value: Any) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _text(value: Any) -> str | None:
    """Extract text from OPS's {"$": "..."} wrappers (also lists of them)."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = [_text(v) for v in value]
        return " ".join(p for p in parts if p) or None
    if isinstance(value, dict):
        if "$" in value:
            return str(value["$"])
        if "p" in value:
            return _text(value["p"])
    return None


def _date(value: str | None) -> date | None:
    if value and re.fullmatch(r"\d{8}", value):
        try:
            return date(int(value[:4]), int(value[4:6]), int(value[6:]))
        except ValueError:
            return None
    return None


def _pick_lang(items: Any, preferred: str = "en") -> Any:
    """From several language versions, prefer English, else the first."""
    items = _as_list(items)
    for item in items:
        if isinstance(item, dict) and str(item.get("@lang", "")).lower() == preferred:
            return item
    return items[0] if items else None


def _clean_party(name: str) -> str:
    # epodoc-format names look like "ACME CORP [US]"; drop the country tag and comma
    return re.sub(r"\s*\[[A-Z]{2}\]\s*$", "", name).strip().rstrip(",")


def build_cql(query: PatentQuery) -> str:
    """Translate our query into OPS CQL. Double quotes in user text are removed."""

    def safe(text: str) -> str:
        return re.sub(r'["\\]', " ", text).strip()

    parts = []
    words = safe(query.keywords)
    if words:
        parts.append(f'ta all "{words}"')  # all words must appear in title or abstract
    for code in query.cpc:
        code = safe(code).replace(" ", "")
        if code:
            parts.append(f"cpc={code}")
    if query.applicant and safe(query.applicant):
        parts.append(f'pa all "{safe(query.applicant)}"')
    if query.date_from and query.date_to:
        parts.append(f'pd within "{query.date_from:%Y%m%d} {query.date_to:%Y%m%d}"')
    elif query.date_from:
        parts.append(f"pd>={query.date_from:%Y%m%d}")
    elif query.date_to:
        parts.append(f"pd<={query.date_to:%Y%m%d}")
    if not parts:
        raise ValueError("A patent search needs keywords, a CPC code or an applicant.")
    return " and ".join(parts)


def parse_exchange_document(doc: dict) -> PatentRecord:
    """One <exchange-document> (bibliographic data + abstract) → PatentRecord."""
    biblio = doc.get("bibliographic-data", {})
    country = doc.get("@country")
    number = doc.get("@doc-number")
    kind = doc.get("@kind")

    publication_date = None
    for doc_id in _as_list(biblio.get("publication-reference", {}).get("document-id")):
        if doc_id.get("@document-id-type") == "docdb":
            country = country or _text(doc_id.get("country"))
            number = number or _text(doc_id.get("doc-number"))
            kind = kind or _text(doc_id.get("kind"))
            publication_date = _date(_text(doc_id.get("date")))
    filing_date = None
    for doc_id in _as_list(biblio.get("application-reference", {}).get("document-id")):
        filing_date = filing_date or _date(_text(doc_id.get("date")))
    priority_dates = [
        _date(_text(doc_id.get("date")))
        for claim in _as_list(biblio.get("priority-claims", {}).get("priority-claim"))
        for doc_id in _as_list(claim.get("document-id"))
    ]
    priority_dates = [d for d in priority_dates if d]

    parties = biblio.get("parties", {})

    def names(group: str, item: str, name_key: str) -> list[str]:
        entries = _as_list(parties.get(group, {}).get(item))
        # Prefer the normalised "epodoc" spelling; fall back to "original"
        chosen = [e for e in entries if e.get("@data-format") == "epodoc"] or entries
        out = [_clean_party(_text(e.get(name_key, {}).get("name")) or "") for e in chosen]
        return list(dict.fromkeys(n for n in out if n))

    cpc_codes = []
    for pc in _as_list(biblio.get("patent-classifications", {}).get("patent-classification")):
        try:
            code = (
                f"{_text(pc['section'])}{_text(pc['class'])}{_text(pc['subclass'])}"
                f"{_text(pc['main-group'])}/{_text(pc['subgroup'])}"
            )
        except KeyError:
            continue
        cpc_codes.append(code.replace(" ", ""))

    title = _text(_pick_lang(biblio.get("invention-title")))
    abstract = _text(_pick_lang(doc.get("abstract")))
    publication = parse_publication_number(f"{country}{number}{kind or ''}")
    return PatentRecord(
        source="epo",
        publication_number=publication.normalized,
        country=publication.country,
        kind_code=publication.kind,
        family_id=doc.get("@family-id"),
        title=title,
        abstract=abstract,
        applicants=names("applicants", "applicant", "applicant-name"),
        inventors=names("inventors", "inventor", "inventor-name"),
        cpc_codes=list(dict.fromkeys(cpc_codes)),
        publication_date=publication_date,
        filing_date=filing_date,
        priority_date=min(priority_dates) if priority_dates else None,
        url=publication.espacenet_url,
        raw=doc,
    )


def parse_search_response(body: dict) -> tuple[int, list[PatentRecord]]:
    search = body.get("ops:world-patent-data", {}).get("ops:biblio-search", {})
    total = int(search.get("@total-result-count", 0) or 0)
    documents = _as_list(search.get("ops:search-result", {}).get("exchange-documents"))
    records = []
    for wrapper in documents:
        for doc in _as_list(wrapper.get("exchange-document")):
            try:
                records.append(parse_exchange_document(doc))
            except (ValueError, KeyError, TypeError) as exc:
                logger.warning("Skipping unparseable EPO document: %s", type(exc).__name__)
    return total, records


def parse_biblio_response(body: dict) -> list[PatentRecord]:
    """Response of /publication/docdb/<number>/biblio → records (one per kind code)."""
    wrappers = _as_list(body.get("ops:world-patent-data", {}).get("exchange-documents"))
    return [
        parse_exchange_document(doc)
        for wrapper in wrappers
        for doc in _as_list(wrapper.get("exchange-document"))
    ]


def parse_fulltext(body: dict, part: str) -> str | None:
    """Extract claims or description text from a full-text response."""
    root = body.get("ops:world-patent-data", {}).get("ftxt:fulltext-documents", {})
    document = _as_list(root.get("ftxt:fulltext-document"))
    if not document:
        return None
    section = _pick_lang(document[0].get(part))
    if not isinstance(section, dict):
        return None
    if part == "claims":
        texts = [
            _text(claim_text)
            for claim in _as_list(section.get("claim"))
            for claim_text in _as_list(claim.get("claim-text"))
        ]
    else:
        texts = [_text(p) for p in _as_list(section.get("p"))]
    paragraphs = [t.strip() for t in texts if t and t.strip()]
    return "\n\n".join(paragraphs) or None


class EpoOpsSource(PatentSource):
    name = "epo"
    label = "EPO Open Patent Services"

    def __init__(
        self,
        key: str,
        secret: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
        http: httpx.Client | None = None,
    ):
        if not key or not secret:
            raise ConfigurationError("EPO_OPS_KEY and EPO_OPS_SECRET are required for EPO search.")
        self._key, self._secret = key, secret
        self._base = base_url.rstrip("/")
        self._http = http or httpx.Client(timeout=timeout)
        self._token: str | None = None
        self._token_expires = 0.0
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ auth

    def _get_token(self, force: bool = False) -> str:
        with self._lock:
            if not force and self._token and time.time() < self._token_expires - 60:
                return self._token
            try:
                response = self._http.post(
                    f"{self._base}/auth/accesstoken",
                    auth=(self._key, self._secret),
                    data={"grant_type": "client_credentials"},
                )
            except httpx.HTTPError as exc:
                raise ExternalServiceError("Could not reach the EPO patent service.") from exc
            if response.status_code in (400, 401):
                raise ConfigurationError(
                    "EPO rejected the OPS credentials. Check EPO_OPS_KEY/SECRET."
                )
            if response.status_code != 200:
                raise ExternalServiceError(
                    f"EPO authentication failed (HTTP {response.status_code})."
                )
            body = response.json()
            self._token = body["access_token"]
            self._token_expires = time.time() + int(body.get("expires_in", 1200))
            return self._token

    def _get(self, path: str, params: dict | None = None) -> dict | None:
        """GET a JSON resource; returns None for 404 (no results / not available)."""
        url = f"{self._base}/rest-services/{path}"
        for attempt in range(2):
            headers = {
                "Authorization": f"Bearer {self._get_token(force=attempt > 0)}",
                "Accept": "application/json",
            }
            try:
                response = self._http.get(url, params=params, headers=headers)
            except httpx.TimeoutException as exc:
                raise ExternalServiceError("The EPO patent service timed out.") from exc
            except httpx.HTTPError as exc:
                raise ExternalServiceError("Could not reach the EPO patent service.") from exc

            throttle = response.headers.get("X-Throttling-Control")
            if throttle:
                logger.debug("EPO throttling: %s", throttle)
            if response.status_code == 200:
                try:
                    return response.json()
                except ValueError as exc:
                    raise ExternalServiceError("EPO returned a malformed response.") from exc
            if response.status_code == 404:
                return None
            if (
                response.status_code in (400, 401)
                and attempt == 0
                and "token" in response.text.lower()
            ):
                continue  # expired token: refresh once and retry
            if response.status_code in (403, 429):
                # Observed: 403 + "X-Rejection-Reason: AnonymousQuotaPerDay" (body is XML)
                reason = response.headers.get("X-Rejection-Reason", "unspecified")
                logger.warning(
                    "EPO rejected request (%s): reason=%s throttle=%s",
                    response.status_code,
                    reason,
                    throttle,
                )
                raise ExternalServiceError(
                    f"EPO fair-use limit reached ({reason}). Try again later; "
                    "earlier results remain available from the cache."
                )
            if response.status_code == 400:
                raise ExternalServiceError("EPO could not understand the search query.")
            raise ExternalServiceError(f"EPO patent service error (HTTP {response.status_code}).")
        raise ExternalServiceError("EPO authentication failed.")

    # ------------------------------------------------------------------ API

    def search(self, query: PatentQuery) -> PatentSearchPage:
        cql = build_cql(query)
        limit = max(1, min(query.limit, MAX_RANGE))
        body = self._get("published-data/search/biblio", {"q": cql, "Range": f"1-{limit}"})
        if body is None:
            return PatentSearchPage(source=self.name, total=0, results=[], query_string=cql)
        total, records = parse_search_response(body)
        return PatentSearchPage(source=self.name, total=total, results=records, query_string=cql)

    def get_details(self, publication_number: str) -> PatentRecord:
        number = parse_publication_number(publication_number)
        base = f"published-data/publication/docdb/{number.docdb}"
        body = self._get(f"{base}/biblio")
        records = parse_biblio_response(body) if body else []
        if not records:
            raise ExternalServiceError(f"EPO has no record of {number.normalized}.")
        # Without a kind code, one number can match several documents (e.g. A1 and B1)
        record = next((r for r in records if r.publication_number == number.normalized), records[0])
        for part in ("claims", "description"):
            text_body = self._get(f"{base}/{part}")
            setattr(record, f"{part}_text", parse_fulltext(text_body, part) if text_body else None)
        record.has_claims = bool(record.claims_text)
        record.has_description = bool(record.description_text)
        return record
