"""Collapse search results that describe the same invention.

One invention is often published many times: an application (EP…A1) and a grant
(EP…B1), plus equivalents in other countries (US, WO, CN…). Together these form a
*patent family*. Showing all of them would waste the user's attention and the
agent's import budget, so we keep one representative per family and list the
others as "also published as".

Grouping key: the source's family ID when present, otherwise country + number
without the kind code (so A1 and B1 of the same number group together).
"""

import re
from dataclasses import dataclass, field

from app.patents.base import PatentRecord

# Offices for which EPO OPS usually provides full text (claims + description)
_FULLTEXT_OFFICES = ("EP", "WO")
_OFFICE_PREFERENCE = {"EP": 0, "WO": 1, "US": 2, "GB": 3}


@dataclass
class FamilyGroup:
    representative: PatentRecord
    members: list[PatentRecord] = field(default_factory=list)  # excluding the representative

    @property
    def also_published_as(self) -> list[str]:
        return [m.publication_number for m in self.members]


def family_key(record: PatentRecord) -> str:
    if record.family_id:
        return f"family:{record.family_id}"
    base = re.sub(r"[A-Z]\d?$", "", record.publication_number)  # drop kind code
    return f"number:{base}"


def _preference(record: PatentRecord) -> tuple:
    """Lower is better: full text available, preferred office, granted, newer, has abstract."""
    country = record.country or record.publication_number[:2]
    granted = (record.kind_code or "").startswith(("B", "C"))
    newest = -(record.publication_date.toordinal() if record.publication_date else 0)
    return (
        country not in _FULLTEXT_OFFICES,
        _OFFICE_PREFERENCE.get(country, 9),
        not granted,
        not record.abstract,
        newest,
    )


def group_by_family(records: list[PatentRecord]) -> list[FamilyGroup]:
    """Group records, keeping the order in which each family first appeared."""
    groups: dict[str, list[PatentRecord]] = {}
    for record in records:
        groups.setdefault(family_key(record), []).append(record)
    result = []
    for members in groups.values():
        unique = list({m.publication_number: m for m in members}.values())
        best = min(unique, key=_preference)
        result.append(FamilyGroup(best, [m for m in unique if m is not best]))
    return result
