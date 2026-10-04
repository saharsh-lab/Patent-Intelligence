"""Which patent sources exist, which are configured, and how to build them."""

from dataclasses import dataclass

from app.core.config import Settings
from app.core.errors import AppError
from app.patents.base import PatentSource
from app.patents.demo import DemoPatentSource
from app.patents.epo import EpoOpsSource


@dataclass
class SourceStatus:
    name: str
    label: str
    status: str  # "available" | "not_configured" | "planned"
    note: str


def source_statuses(settings: Settings) -> list[SourceStatus]:
    epo_ready = bool(
        settings.epo_ops_key.get_secret_value() and settings.epo_ops_secret.get_secret_value()
    )
    statuses = [
        SourceStatus(
            "epo",
            "EPO Open Patent Services",
            "available" if epo_ready else "not_configured",
            "Worldwide bibliographic data; full text for EP, WO and some other offices."
            if epo_ready
            else "Set EPO_OPS_KEY and EPO_OPS_SECRET (free registration at developers.epo.org).",
        ),
        SourceStatus("lens", "Lens.org", "planned", "Cross-check source; client not built yet."),
        SourceStatus("uspto", "USPTO Open Data", "planned", "Client not built yet."),
    ]
    if settings.patent_demo_source:
        statuses.append(
            SourceStatus("demo", "Demo (synthetic data)", "available", "Fake records, country XX.")
        )
    return statuses


def build_sources(settings: Settings) -> dict[str, PatentSource]:
    sources: dict[str, PatentSource] = {}
    if settings.epo_ops_key.get_secret_value() and settings.epo_ops_secret.get_secret_value():
        sources["epo"] = EpoOpsSource(
            settings.epo_ops_key.get_secret_value(),
            settings.epo_ops_secret.get_secret_value(),
            base_url=settings.epo_ops_base_url,
            timeout=settings.patent_http_timeout_seconds,
        )
    if settings.patent_demo_source:
        sources["demo"] = DemoPatentSource()
    return sources


def choose_source(sources: dict[str, PatentSource], number: str) -> str:
    """Which configured source to fetch a publication number from."""
    if number.startswith("XX") and "demo" in sources:
        return "demo"
    if "epo" in sources and not number.startswith("XX"):
        return "epo"
    raise AppError(
        f"Cannot fetch {number}: no suitable patent source is configured.", code="no_patent_source"
    )


_cache: dict[tuple, dict[str, PatentSource]] = {}


def get_patent_sources_for(settings: Settings) -> dict[str, PatentSource]:
    """Reuse source objects (EPO keeps its access token) while settings are unchanged."""
    key = (
        settings.epo_ops_key.get_secret_value(),
        settings.epo_ops_secret.get_secret_value(),
        settings.epo_ops_base_url,
        settings.patent_demo_source,
    )
    if key not in _cache:
        _cache.clear()
        _cache[key] = build_sources(settings)
    return _cache[key]
