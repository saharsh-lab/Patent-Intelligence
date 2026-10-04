"""Reranking: a slower, more accurate second opinion on the top candidates.

Embedding search encodes the question and each passage *separately*, then
compares the vectors, so it's fast enough to scan the whole database but coarse.
A cross-encoder reads the question and a passage *together* and outputs one
relevance score. It's much more accurate but too slow to run on everything, so
we use it only to reorder the ~30 candidates that retrieval already found.

Whether this helps on patent text is measured in Experiment D.
"""

import logging
import re
import threading
from abc import ABC, abstractmethod
from functools import lru_cache

from app.core.config import Settings, get_settings
from app.core.errors import ConfigurationError

logger = logging.getLogger(__name__)


class Reranker(ABC):
    name: str

    @abstractmethod
    def score(self, query: str, passages: list[str]) -> list[float]:
        """Relevance score per passage (higher = more relevant)."""


class FakeReranker(Reranker):
    """Fraction of query words that appear in the passage. Tests only."""

    name = "fake-overlap"
    _WORD = re.compile(r"[a-z0-9]{3,}")

    def score(self, query: str, passages: list[str]) -> list[float]:
        query_words = set(self._WORD.findall(query.lower()))
        if not query_words:
            return [0.0] * len(passages)
        return [
            len(query_words & set(self._WORD.findall(p.lower()))) / len(query_words)
            for p in passages
        ]


class CrossEncoderReranker(Reranker):
    def __init__(self, model_name: str):
        self.name = model_name
        self._model = None
        self._lock = threading.Lock()

    def _load(self):
        with self._lock:
            if self._model is None:
                try:
                    from sentence_transformers import CrossEncoder
                except ImportError as exc:
                    raise ConfigurationError(
                        "The local reranker needs: pip install -r requirements-ml.txt"
                    ) from exc
                logger.info("Loading reranker %s (first time downloads it)", self.name)
                self._model = CrossEncoder(self.name)
        return self._model

    def score(self, query: str, passages: list[str]) -> list[float]:
        if not passages:
            return []
        scores = self._load().predict([(query, p) for p in passages], show_progress_bar=False)
        return [float(s) for s in scores]


def build_reranker(settings: Settings) -> Reranker | None:
    if not settings.reranker_enabled:
        return None
    if settings.reranker_provider == "fake":
        return FakeReranker()
    return CrossEncoderReranker(settings.reranker_model)


@lru_cache
def _cached_cross_encoder(model_name: str) -> CrossEncoderReranker:
    return CrossEncoderReranker(model_name)


def get_reranker_for(settings: Settings) -> Reranker | None:
    """Like build_reranker, but reuses a loaded model across requests."""
    if settings.reranker_enabled and settings.reranker_provider == "local":
        return _cached_cross_encoder(settings.reranker_model)
    return build_reranker(settings)


def get_reranker() -> Reranker | None:
    return get_reranker_for(get_settings())
