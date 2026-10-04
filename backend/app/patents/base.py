"""The common interface every patent data source implements.

The rest of the system only knows about `PatentSource`, `PatentQuery` and
`PatentRecord`. Adding Lens or USPTO later means writing one new class; nothing
else changes. (This is the "modular, replaceable API integration" requirement.)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class PatentQuery:
    keywords: str = ""  # free text, matched against title + abstract
    cpc: list[str] = field(default_factory=list)  # e.g. ["H01M10/48"]
    applicant: str | None = None
    date_from: date | None = None  # publication date range
    date_to: date | None = None
    limit: int = 25

    def is_empty(self) -> bool:
        return not (self.keywords.strip() or self.cpc or self.applicant)


@dataclass
class PatentRecord:
    source: str
    publication_number: str  # normalised, e.g. "EP1234567A1"
    country: str | None = None
    kind_code: str | None = None
    family_id: str | None = None
    title: str | None = None
    abstract: str | None = None
    applicants: list[str] = field(default_factory=list)
    inventors: list[str] = field(default_factory=list)
    cpc_codes: list[str] = field(default_factory=list)
    publication_date: date | None = None
    filing_date: date | None = None
    priority_date: date | None = None
    claims_text: str | None = None
    description_text: str | None = None
    url: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    # Which parts are available — full text is not published for every country
    has_claims: bool = False
    has_description: bool = False


@dataclass
class PatentSearchPage:
    source: str
    total: int  # total hits reported by the source (may exceed len(results))
    results: list[PatentRecord]
    query_string: str  # the query actually sent, for transparency and logging


class PatentSource(ABC):
    name: str  # short id: "epo", "lens", "demo"
    label: str  # human name for the UI

    @abstractmethod
    def search(self, query: PatentQuery) -> PatentSearchPage: ...

    @abstractmethod
    def get_details(self, publication_number: str) -> PatentRecord:
        """Bibliographic data plus claims/description where the source has them."""
