"""Record REAL EPO OPS responses (needs EPO_OPS_KEY/SECRET in .env) and check our parser.

    cd backend && .venv/bin/python -m scripts.record_epo_fixtures ["search words"]

Saves tests/fixtures/epo/recorded_*.json. The test suite then also parses these, so
any difference between the documented and the real response format shows up as a
failing test instead of a silent bug. Uses ~4 requests of your weekly quota.
"""

import json
import sys

import httpx

from app.core.config import get_settings
from app.patents.base import PatentQuery
from app.patents.epo import (
    EpoOpsSource,
    build_cql,
    parse_biblio_response,
    parse_fulltext,
    parse_search_response,
)
from app.patents.numbers import parse_publication_number
from tests.helpers import FIXTURES

OUT = FIXTURES / "epo"


def main() -> None:
    settings = get_settings()
    key, secret = (
        settings.epo_ops_key.get_secret_value(),
        settings.epo_ops_secret.get_secret_value(),
    )
    if not (key and secret):
        sys.exit("Set EPO_OPS_KEY and EPO_OPS_SECRET in .env first.")
    source = EpoOpsSource(key, secret, base_url=settings.epo_ops_base_url)
    words = sys.argv[1] if len(sys.argv) > 1 else "battery thermal management"

    search = source._get(  # noqa: SLF001 - raw response wanted on purpose
        "published-data/search/biblio",
        {"q": build_cql(PatentQuery(keywords=words)), "Range": "1-10"},
    )
    if not search:
        sys.exit(f"No results for {words!r}; try other words.")
    (OUT / "recorded_search.json").write_text(json.dumps(search, indent=1))
    total, records = parse_search_response(search)
    print(f"search: total={total}, parsed {len(records)} records")
    for r in records[:5]:
        print(f"  {r.publication_number:16} {r.publication_date} {(r.title or '')[:60]!r}")

    target = next((r for r in records if r.country == "EP"), records[0])
    number = parse_publication_number(target.publication_number)
    base = f"published-data/publication/docdb/{number.docdb}"
    for part in ("biblio", "claims", "description"):
        try:
            body = source._get(f"{base}/{part}")  # noqa: SLF001
        except httpx.HTTPError as exc:
            print(f"{part}: request failed ({exc})")
            continue
        if body is None:
            print(f"{part}: not available for {number.normalized}")
            continue
        (OUT / f"recorded_{part}.json").write_text(json.dumps(body, indent=1))
        if part == "biblio":
            parsed = parse_biblio_response(body)
            print(
                f"biblio: {len(parsed)} record(s); title={parsed[0].title!r}"
                if parsed
                else "biblio: PARSE FAILED"
            )
        else:
            text = parse_fulltext(body, part)
            print(f"{part}: {len(text or '')} chars" + ("" if text else "  <-- PARSE FAILED"))
    print(f"\nSaved to {OUT}. Now run: .venv/bin/pytest tests/test_phase5_epo.py -k recorded")


if __name__ == "__main__":
    main()
