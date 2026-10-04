"""A built-in source of SYNTHETIC patents, for trying the UI without API keys.

All records use the made-up country code "XX" so they can never be mistaken for
real publications. Enabled only with PATENT_DEMO_SOURCE=true; never use it in
experiments.
"""

import re
from datetime import date

from app.core.errors import NotFoundError
from app.patents.base import PatentQuery, PatentRecord, PatentSearchPage, PatentSource

_NOTE = "SYNTHETIC DEMO RECORD - not a real patent."

_RECORDS = [
    PatentRecord(
        source="demo",
        publication_number="XX0000001A1",
        country="XX",
        kind_code="A1",
        family_id="demo-1",
        title="Liquid-cooled battery pack with per-cell temperature estimation",
        abstract=(
            "A battery pack has a thermistor on every cell. A controller estimates each "
            "cell's core temperature from surface temperature and current and raises the "
            "coolant pump speed when any estimate exceeds a limit."
        ),
        applicants=["Demo Energy Systems"],
        inventors=["A. Example"],
        cpc_codes=["H01M10/486", "H01M10/613"],
        publication_date=date(2021, 3, 4),
        filing_date=date(2019, 9, 12),
        claims_text=(
            "1. A battery pack comprising: a plurality of cells; a thermistor attached to each "
            "cell; a coolant pump; and a controller configured to estimate a core temperature "
            "of each cell and to increase a speed of the coolant pump when an estimated core "
            "temperature exceeds a limit.\n\n"
            "2. The battery pack of claim 1, wherein the core temperature is estimated from a "
            "surface temperature and a current of the cell."
        ),
        description_text=(
            "The pack contains sixteen prismatic cells cooled by a cold plate. "
            "Each cell carries a thermistor. The controller runs a lumped thermal model.\n\n"
            "When the hottest estimated core temperature exceeds 42 degrees Celsius, the pump "
            f"speed is increased in steps of ten percent.\n\n{_NOTE}"
        ),
    ),
    PatentRecord(
        source="demo",
        publication_number="XX0000002B1",
        country="XX",
        kind_code="B1",
        family_id="demo-2",
        title="Wireless charger that detects metal objects by coil quality factor",
        abstract=(
            "An inductive charging pad measures the quality factor of its transmitter coil "
            "before power transfer and blocks charging when a metal object is present."
        ),
        applicants=["Demo Charging Ltd"],
        inventors=["B. Sample"],
        cpc_codes=["H02J50/60", "H02J50/12"],
        publication_date=date(2022, 6, 15),
        filing_date=date(2020, 1, 20),
        claims_text=(
            "1. A wireless charging pad comprising a transmitter coil, an inverter, and a "
            "detection circuit that measures a quality factor of the coil and disables the "
            "inverter when the quality factor is below a threshold."
        ),
        description_text=f"Coins and keys reduce the coil quality factor.\n\n{_NOTE}",
    ),
    PatentRecord(
        source="demo",
        publication_number="XX0000003A1",
        country="XX",
        kind_code="A1",
        family_id="demo-3",
        title="Battery management system with immersion cooling fluid",
        abstract=(
            "Battery cells are immersed in a dielectric fluid; temperature sensors in the "
            "fluid allow a controller to regulate fluid circulation."
        ),
        applicants=["Demo Energy Systems"],
        inventors=["C. Placeholder"],
        cpc_codes=["H01M10/6567"],
        publication_date=date(2023, 11, 2),
        filing_date=date(2022, 2, 8),
        claims_text=(
            "1. A battery system comprising cells immersed in a dielectric fluid, a fluid "
            "temperature sensor, and a controller regulating circulation of the fluid."
        ),
        description_text=f"The dielectric fluid is circulated by a pump.\n\n{_NOTE}",
    ),
]

for _record in _RECORDS:
    _record.has_claims = True
    _record.has_description = True
    _record.url = None


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{3,}", text.lower()))


class DemoPatentSource(PatentSource):
    name = "demo"
    label = "Demo (synthetic data)"

    def search(self, query: PatentQuery) -> PatentSearchPage:
        wanted = _words(query.keywords)
        scored = []
        for record in _RECORDS:
            if query.cpc and not any(
                code.startswith(prefix.replace(" ", ""))
                for prefix in query.cpc
                for code in record.cpc_codes
            ):
                continue
            if (
                query.applicant
                and query.applicant.lower() not in " ".join(record.applicants).lower()
            ):
                continue
            if query.date_from and record.publication_date < query.date_from:
                continue
            if query.date_to and record.publication_date > query.date_to:
                continue
            overlap = len(wanted & _words(f"{record.title} {record.abstract}")) if wanted else 1
            if overlap:
                scored.append((overlap, record))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        results = [_brief(r) for _, r in scored[: query.limit]]
        return PatentSearchPage(
            source=self.name, total=len(scored), results=results, query_string=query.keywords
        )

    def get_details(self, publication_number: str) -> PatentRecord:
        for record in _RECORDS:
            if record.publication_number == publication_number:
                return record
        raise NotFoundError(f"No demo patent {publication_number}.")


def _brief(record: PatentRecord) -> PatentRecord:
    """Search results carry bibliographic data only, like real sources."""
    from dataclasses import replace

    return replace(record, claims_text=None, description_text=None)
