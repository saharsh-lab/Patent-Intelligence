"""Application settings, loaded from environment variables / the root `.env` file.

Every tunable value lives here so that experiments are reproducible: an
experiment run can store a snapshot of these settings next to its results.
Secrets use `SecretStr`, which prints as '**********' and is never logged.
"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# backend/app/core/config.py -> parents[3] is the project root
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",  # .env also holds docker-only variables (POSTGRES_*)
    )

    # --- Application ---
    app_name: str = "Patent Intelligence API"
    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    # --- Database ---
    database_url: str = (
        "postgresql+psycopg://patent_rag:change_me_local_only@localhost:5434/patent_rag"
    )
    test_database_url: str = (
        "postgresql+psycopg://patent_rag:change_me_local_only@localhost:5434/patent_rag_test"
    )
    # Experiments get their own database: the runner deletes and re-ingests its corpus
    eval_database_url: str = (
        "postgresql+psycopg://patent_rag:change_me_local_only@localhost:5434/patent_rag_eval"
    )

    # --- Hardening (Phase 11) ---
    # Requests per minute per client. Behind the bundled Next.js proxy every browser
    # request arrives from the proxy, so these act as one shared budget (a cost guard).
    rate_limit_enabled: bool = True
    rate_limit_llm_per_minute: int = Field(default=20, ge=1)  # /ask, /compare
    rate_limit_ingest_per_minute: int = Field(default=30, ge=1)  # uploads, patent API calls
    rate_limit_default_per_minute: int = Field(default=600, ge=1)
    # Trust X-Forwarded-For only behind a proxy you control that overwrites it
    trust_proxy_headers: bool = False
    max_json_body_kb: int = Field(default=256, ge=16, le=10_240)

    # --- Uploads ---
    max_upload_mb: int = Field(default=25, gt=0, le=200)
    upload_dir: Path = PROJECT_ROOT / "data" / "uploads"
    allowed_extensions: tuple[str, ...] = (".pdf", ".docx", ".txt")
    max_pdf_pages: int = Field(default=500, gt=0)

    # --- Chunking ---
    # section_aware: split along patent sections, one chunk per claim (our method)
    # fixed: sliding window that ignores structure (baseline for Experiment B)
    chunking_strategy: Literal["section_aware", "fixed"] = "section_aware"
    chunk_max_tokens: int = Field(default=400, ge=50, le=2000)
    chunk_overlap_tokens: int = Field(default=60, ge=0, le=500)

    # --- LLM ---
    llm_provider: Literal["fake", "openai_compatible"] = "fake"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: SecretStr = SecretStr("")
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=1200, gt=0)
    llm_timeout_seconds: float = Field(default=120.0, gt=0)
    # Sent as `reasoning_effort` when set. "none" turns off the slow "thinking" phase of
    # reasoning models (e.g. Qwen3 on Ollama: ~10x faster). Empty = don't send.
    llm_reasoning_effort: str = ""
    # Prices in USD per 1M tokens, used to estimate cost. Set them from your provider's
    # price page; 0 = free/local (e.g. Ollama). We do not hard-code prices.
    llm_price_input_per_1m: float = Field(default=0.0, ge=0)
    llm_price_output_per_1m: float = Field(default=0.0, ge=0)

    # --- Embeddings / reranking ---
    embedding_provider: Literal["fake", "local", "openai_compatible"] = "fake"
    embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = Field(default=1024, gt=0, le=2000)  # HNSW index limit is 2000
    embedding_batch_size: int = Field(default=16, gt=0, le=256)
    # Only for EMBEDDING_PROVIDER=openai_compatible; empty = reuse the LLM_* values
    embedding_base_url: str = ""
    embedding_api_key: SecretStr = SecretStr("")
    reranker_enabled: bool = False
    # fake = word-overlap scorer for tests; local = cross-encoder via sentence-transformers
    reranker_provider: Literal["fake", "local"] = "local"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"

    # --- Retrieval (Phase 3) ---
    # hybrid = vector + keyword fused with Reciprocal Rank Fusion; others for experiments
    retrieval_mode: Literal["hybrid", "vector", "keyword"] = "hybrid"
    retrieval_top_k: int = Field(default=6, ge=1, le=20)  # passages given to the LLM
    retrieval_candidate_k: int = Field(default=30, ge=1, le=200)  # per method, before fusion
    rrf_k: int = Field(default=60, ge=1)
    # Below this best vector similarity (and with no keyword match) we answer
    # "insufficient evidence" without calling the LLM. Calibrated in Phase 9.
    retrieval_min_similarity: float = Field(default=0.35, ge=-1.0, le=1.0)
    max_context_tokens: int = Field(default=3000, ge=200, le=100_000)

    # --- Agent (Phase 6) ---
    # Pipeline used by /ask when the request doesn't say: agentic (LangGraph) or baseline RAG
    default_pipeline: Literal["agentic", "baseline"] = "agentic"
    # How the agent classifies questions: rules (free), llm, or auto (llm unless LLM is fake)
    agent_planner: Literal["auto", "rules", "llm"] = "auto"
    agent_similar_import_limit: int = Field(default=3, ge=0, le=10)
    agent_max_recoveries: int = Field(default=1, ge=0, le=3)
    # When the library cannot answer a general question, search the patent databases,
    # import the most relevant full-text patents and answer from them.
    agent_live_fallback: bool = True
    agent_live_import_limit: int = Field(default=3, ge=1, le=5)
    # select: the agent chooses tools per question | all: run every applicable tool
    # (no selection), the control condition of Experiment F
    agent_tool_policy: Literal["select", "all"] = "select"

    # --- Claim-level verification (Phase 8) ---
    # off: no checks | report: verify and show verdicts | regenerate: also rewrite the
    # answer (with extra retrieval) when grounding is below the threshold.
    # The baseline pipeline never regenerates (it stays the "conventional RAG" control).
    verify_mode: Literal["off", "report", "regenerate"] = "regenerate"
    # nli: local entailment model (free) | llm_judge: ask the LLM | lexical: word overlap
    # auto: nli if sentence-transformers is installed, else lexical
    # auto: nli_llm with a real LLM (NLI, guarded word-overlap rescue, LLM second opinion on
    # what is still flagged), nli_lexical with the fake LLM, lexical without the ML extras
    verifier_method: Literal["auto", "nli", "nli_lexical", "nli_llm", "llm_judge", "lexical"] = (
        "auto"
    )
    # An uncited statement that a passage supports counts as supported (see checker.py)
    verifier_uncited_supported: bool = True
    verifier_nli_model: str = "cross-encoder/nli-deberta-v3-xsmall"
    grounding_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    max_regenerations: int = Field(default=1, ge=0, le=2)

    # --- Patent sources ---
    epo_ops_key: SecretStr = SecretStr("")
    epo_ops_secret: SecretStr = SecretStr("")
    uspto_api_key: SecretStr = SecretStr("")
    lens_api_token: SecretStr = SecretStr("")
    patent_cache_ttl_hours: int = Field(default=168, ge=0)
    # Keyword searches fetch this many candidates and keep the most relevant (OPS max 100)
    patent_search_pool: int = Field(default=50, ge=10, le=100)
    epo_ops_base_url: str = "https://ops.epo.org/3.2"
    patent_http_timeout_seconds: float = Field(default=30.0, gt=0)
    # A built-in source of SYNTHETIC patents (country code "XX") so the search UI can be
    # tried before real API keys exist. Never enable it for experiments.
    patent_demo_source: bool = False

    # --- Evaluation (Phase 9) ---
    # Datasets, experiment configs, human labels and result folders
    experiments_dir: Path = PROJECT_ROOT / "experiments"

    # --- Patent monitoring ---
    # Check all active watches every N hours inside the API process (0 = only on demand /
    # via `python -m scripts.check_watches` from cron)
    watch_check_interval_hours: float = Field(default=0, ge=0, le=168)

    # --- Observability ---
    langsmith_api_key: SecretStr = SecretStr("")
    langsmith_tracing: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Allow CORS_ORIGINS to be written as a comma-separated string in .env."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("upload_dir", "experiments_dir", mode="after")
    @classmethod
    def _resolve_upload_dir(cls, value: Path) -> Path:
        """Relative paths are interpreted from the project root, not the CWD."""
        return value if value.is_absolute() else PROJECT_ROOT / value

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def enabled_patent_sources(self) -> list[str]:
        """Patent sources whose credentials are configured."""
        sources = []
        if self.epo_ops_key.get_secret_value() and self.epo_ops_secret.get_secret_value():
            sources.append("epo")
        if self.uspto_api_key.get_secret_value():
            sources.append("uspto")
        if self.lens_api_token.get_secret_value():
            sources.append("lens")
        if self.patent_demo_source:
            sources.append("demo")
        return sources


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (read the environment once per process)."""
    return Settings()
