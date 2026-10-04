"""Build an evaluation corpus of real patents as plain-text files.

    python -m scripts.build_corpus --out ../experiments/datasets/real_v1/corpus \\
        US9178361B2 US11646607B2 ...

For each publication number: download the public patent page from Google Patents
(https://patents.google.com/patent/<number>/en; robots.txt allows /patent/ pages, not
the search API, which this script never uses), keep the raw HTML in data/patent_html/
(so re-runs don't download again), and write <number>.txt with standard headings
(TITLE OF INVENTION, ABSTRACT, BACKGROUND, ..., CLAIMS) that the ingestion pipeline's
section detection understands. Paragraph numbers are kept as [0001].

One request every 2 seconds. Once EPO OPS keys are configured, the app's own EPO import
is the preferred source; this script exists so the dataset can be built without keys.
"""

import argparse
import re
import sys
import time
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE = PROJECT_ROOT / "data" / "patent_html"
URL = "https://patents.google.com/patent/{number}/en"
# Granted patents and applications use different markup for the same things
PARAGRAPH_CLASSES = {"description-paragraph", "description-line"}
CLAIM_CLASSES = {"claim", "claim-dependent"}
NUMBER = re.compile(r"^[A-Z]{2}\d{4,12}[A-Z]\d?$")


class PatentPage(HTMLParser):
    """Collects abstract, description headings/paragraphs and claims from the page."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.blocks: list[tuple[str, str]] = []  # (kind, text): abstract|heading|para|claim
        self._section: str | None = None  # abstract | description | claims
        self._section_depth = 0
        self._capture: tuple[str, int] | None = None  # (kind, depth at start)
        self._buffer: list[str] = []
        self._depth = 0
        self._para_num = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta" and attrs.get("name") == "DC.title":
            self.title = " ".join((attrs.get("content") or "").split())
        if tag in ("br", "img", "meta", "link", "input"):
            return  # void elements: no end tag, no depth
        self._depth += 1
        prop = attrs.get("itemprop")
        if tag == "section" and prop in ("abstract", "description", "claims"):
            self._section, self._section_depth = prop, self._depth
            return
        if self._section is None or self._capture is not None:
            if self._capture and tag == "div" and "claim-text" in (attrs.get("class") or ""):
                self._buffer.append("\n")  # claim elements on their own lines
            return
        classes = attrs.get("class") or ""
        if self._section == "abstract" and tag == "div" and "abstract" in classes:
            self._start("abstract")
        elif self._section == "description" and tag == "heading":
            self._start("heading")
        elif self._section == "description" and classes.strip() in PARAGRAPH_CLASSES:
            self._para_num = attrs.get("num") or ""
            self._start("para")
        elif (
            self._section == "claims"
            and tag == "div"
            and classes.strip() in CLAIM_CLASSES
            and (attrs.get("id") or "").startswith("CLM-")
        ):
            self._start("claim")

    def _start(self, kind: str) -> None:
        self._capture, self._buffer = (kind, self._depth), []

    def handle_endtag(self, tag):
        if tag in ("br", "img", "meta", "link", "input"):
            return
        if self._capture and self._depth == self._capture[1]:
            kind = self._capture[0]
            text = re.sub(r"[ \t]+", " ", "".join(self._buffer))
            text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
            if kind == "para" and self._para_num:
                text = f"[{self._para_num}] {text}"
            if text:
                self.blocks.append((kind, text))
            self._capture = None
        if self._section and self._depth == self._section_depth:
            self._section = None
        self._depth -= 1

    def handle_data(self, data):
        if self._capture:
            self._buffer.append(data)


def fetch(number: str) -> str:
    CACHE.mkdir(parents=True, exist_ok=True)
    cached = CACHE / f"{number}.html"
    if cached.exists():
        return cached.read_text(encoding="utf-8")
    response = httpx.get(
        URL.format(number=number),
        headers={"User-Agent": "Mozilla/5.0 (research)"},
        timeout=30,
        follow_redirects=True,
    )
    response.raise_for_status()
    html = response.text
    cached.write_text(html, encoding="utf-8")
    time.sleep(2)  # be polite
    return html


def to_text(number: str, page: PatentPage) -> str:
    lines = [
        f"PUBLICATION NUMBER: {number}",
        f"Source: {URL.format(number=number)} (public patent document), "
        f"retrieved {datetime.now(UTC).date().isoformat()}.",
        "",
        "TITLE OF INVENTION",
        "",
        page.title,
        "",
    ]
    abstract = [t for k, t in page.blocks if k == "abstract"]
    if abstract:
        lines += ["ABSTRACT", "", *abstract, ""]
    for kind, text in page.blocks:
        if kind == "heading":
            lines += [text.upper(), ""]
        elif kind == "para":
            lines += [text, ""]
    claims = [t for k, t in page.blocks if k == "claim"]
    if claims:
        lines += ["CLAIMS", ""]
        for claim in claims:
            lines += [" ".join(claim.split("\n")), ""]
    return "\n".join(lines).strip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("numbers", nargs="+", help="publication numbers, e.g. US9178361B2")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    failures = 0
    for number in args.numbers:
        number = number.strip().upper()
        if not NUMBER.match(number):
            print(f"{number}: not a publication number with kind code, skipped")
            failures += 1
            continue
        try:
            page = PatentPage()
            page.feed(fetch(number))
        except (OSError, httpx.HTTPError) as exc:
            print(f"{number}: download failed ({exc})")
            failures += 1
            continue
        kinds = [k for k, _ in page.blocks]
        if "claim" not in kinds or "para" not in kinds:
            print(f"{number}: no English full text (claims/description) on the page, skipped")
            failures += 1
            continue
        (args.out / f"{number}.txt").write_text(to_text(number, page), encoding="utf-8")
        print(
            f"{number}: {page.title[:60]!r} — {kinds.count('para')} paragraphs, "
            f"{kinds.count('claim')} claims"
        )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
