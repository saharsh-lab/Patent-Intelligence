"""Experiment configs: which dataset, which variants, which settings.

    name: exp_a_pipelines
    dataset: ../datasets/dev/dataset.yaml   # relative to this file
    repeats: 1
    settings: {retrieval_top_k: 6}          # shared by all variants
    variants:
      - {name: baseline, pipeline: baseline}
      - {name: agentic,  pipeline: agentic}

A variant's settings = `.env` values, overridden by `settings`, overridden by the
variant's own `settings`. Names are the Settings fields (case-insensitive), so
anything in `.env` can be varied. Unknown names are rejected: a typo would otherwise
silently run the default and produce a misleading result.
"""

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.core.config import Settings

# Not experiment variables: where data lives, credentials, and server plumbing
FORBIDDEN_OVERRIDES = {
    "database_url",
    "test_database_url",
    "eval_database_url",
    "upload_dir",
    "experiments_dir",
    "cors_origins",
    "app_env",
    "llm_api_key",
    "embedding_api_key",
    "epo_ops_key",
    "epo_ops_secret",
    "uspto_api_key",
    "lens_api_token",
    "langsmith_api_key",
}


class ConfigError(ValueError):
    pass


def _lower_keys(value: Any) -> Any:
    return {str(k).lower(): v for k, v in (value or {}).items()}


class VariantConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(pattern=r"^[A-Za-z0-9_.-]{1,40}$")
    pipeline: Literal["baseline", "agentic"]
    settings: dict[str, Any] = {}
    description: str = ""

    @field_validator("settings", mode="before")
    @classmethod
    def _lower(cls, value: Any) -> Any:
        return _lower_keys(value)


class ExperimentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(pattern=r"^[A-Za-z0-9_.-]{1,60}$")
    description: str = ""
    dataset: Path
    repeats: int = Field(default=1, ge=1, le=10)
    eval_k: int = Field(default=5, ge=1, le=50)  # cutoff for precision/recall@k
    seed: int = 0  # bootstrap seed
    settings: dict[str, Any] = {}
    variants: list[VariantConfig] = Field(min_length=1)
    items: list[str] | None = None  # run only these item ids (quick checks)

    @field_validator("settings", mode="before")
    @classmethod
    def _lower(cls, value: Any) -> Any:
        return _lower_keys(value)

    @field_validator("variants")
    @classmethod
    def _unique_names(cls, variants: list[VariantConfig]) -> list[VariantConfig]:
        names = [v.name for v in variants]
        if len(names) != len(set(names)):
            raise ValueError("variant names must be unique")
        return variants


def load_config(path: Path) -> ExperimentConfig:
    path = Path(path).resolve()
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        config = ExperimentConfig.model_validate(raw)
    except (OSError, yaml.YAMLError, ValidationError) as exc:
        raise ConfigError(f"Invalid experiment config {path}:\n{exc}") from exc
    config.dataset = (path.parent / config.dataset).resolve()
    for overrides in [config.settings, *(v.settings for v in config.variants)]:
        check_overrides(overrides)
    return config


def check_overrides(overrides: dict[str, Any]) -> None:
    unknown = set(overrides) - set(Settings.model_fields)
    if unknown:
        raise ConfigError(f"Unknown setting(s) {sorted(unknown)}; see .env.example for names")
    forbidden = set(overrides) & FORBIDDEN_OVERRIDES
    if forbidden:
        raise ConfigError(f"Setting(s) {sorted(forbidden)} cannot be changed by an experiment")


def variant_settings(base: Settings, config: ExperimentConfig, variant: VariantConfig) -> Settings:
    """Validated Settings for one variant (bad values fail here, before any run)."""
    overrides = {**config.settings, **variant.settings}
    check_overrides(overrides)
    # Synthetic demo patents must never leak into results unless a config asks explicitly
    overrides.setdefault("patent_demo_source", False)
    # Added after the experiments were run; off so reruns measure the same system.
    overrides.setdefault("agent_live_fallback", False)
    overrides.setdefault("verifier_uncited_supported", False)
    data = base.model_dump() | overrides
    try:
        # model_validate validates the dict alone: it does not re-read .env
        return Settings.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(f"Variant {variant.name!r}: invalid settings:\n{exc}") from exc


def public_settings(settings: Settings) -> dict[str, Any]:
    """Settings snapshot for result files: secrets and local paths removed."""
    data = settings.model_dump(mode="json")
    for key in FORBIDDEN_OVERRIDES:
        data.pop(key, None)
    data["enabled_patent_sources"] = settings.enabled_patent_sources
    return data
