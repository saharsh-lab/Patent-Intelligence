"""Patent publication numbers: parse the many ways people write them into one form.

The same publication can appear as "EP 1 234 567 A1", "EP1234567A1",
"ep-1234567-a1", "US 10,123,456 B2" or "WO 2020/123456 A1". We normalise to
COUNTRY + NUMBER + KIND ("EP1234567A1"), which is also how EPO's "docdb"
format identifies documents (written there as "EP.1234567.A1").
"""

import re
from dataclasses import dataclass

_PATTERN = re.compile(
    r"^\s*(?P<country>[A-Z]{2})[\s.\-]*(?P<number>\d[\d\s,./\-]*\d|\d)[\s.\-]*(?P<kind>[A-Z]\d?)?\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PublicationNumber:
    country: str
    number: str
    kind: str | None = None

    @property
    def normalized(self) -> str:
        return f"{self.country}{self.number}{self.kind or ''}"

    @property
    def docdb(self) -> str:
        """EPO OPS docdb input format, e.g. 'EP.1234567.A1' (kind optional)."""
        return f"{self.country}.{self.number}" + (f".{self.kind}" if self.kind else "")

    @property
    def espacenet_url(self) -> str:
        return f"https://worldwide.espacenet.com/patent/search?q=pn%3D{self.normalized}"


def parse_publication_number(text: str) -> PublicationNumber:
    match = _PATTERN.match(text or "")
    if not match:
        raise ValueError(f"Not a recognisable publication number: {text!r}")
    digits = re.sub(r"[^\d]", "", match.group("number"))
    kind = match.group("kind")
    return PublicationNumber(
        country=match.group("country").upper(),
        number=digits,
        kind=kind.upper() if kind else None,
    )


def normalize_publication_number(text: str) -> str:
    return parse_publication_number(text).normalized
