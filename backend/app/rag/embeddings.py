"""Step 5 of ingestion: turn text into embeddings (vectors that capture meaning).

Three interchangeable providers, chosen with EMBEDDING_PROVIDER:

- fake:  deterministic "hashing" vectors. Texts sharing words get similar vectors,
         so retrieval still behaves sensibly in tests, at zero cost, offline.
- local: a real embedding model (default BGE-M3) running on this machine via
         sentence-transformers. Free; first use downloads the model (~2.3 GB).
- openai_compatible: any provider exposing the OpenAI /embeddings endpoint.

All vectors are L2-normalised (length 1), so cosine similarity = dot product.
"""

import hashlib
import logging
import math
import re
import threading
import time
from abc import ABC, abstractmethod
from functools import lru_cache

import httpx

from app.core.config import Settings, get_settings
from app.core.errors import ConfigurationError, ExternalServiceError

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    name: str
    dim: int

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed passages that will be stored and searched."""

    def embed_query(self, text: str) -> list[float]:
        """Embed a search query (some models treat queries and passages differently)."""
        return self.embed_documents([text])[0]


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector))
    return [v / norm for v in vector] if norm else vector


class FakeEmbedder(EmbeddingProvider):
    """Feature hashing: each word adds +/-1 at a position chosen by its hash."""

    _WORD = re.compile(r"[a-z0-9]+")
    # Ignore filler words, otherwise every text looks similar to every question
    _STOPWORDS = frozenset(
        [
            "a",
            "an",
            "and",
            "are",
            "as",
            "at",
            "be",
            "by",
            "does",
            "for",
            "from",
            "how",
            "in",
            "is",
            "it",
            "its",
            "of",
            "on",
            "or",
            "that",
            "the",
            "this",
            "to",
            "was",
            "what",
            "when",
            "where",
            "which",
            "who",
            "why",
            "with",
        ]
    )

    def __init__(self, dim: int):
        self.dim = dim
        self.name = f"fake-hash-{dim}"

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        vector[0] = 1e-3  # never all-zero: cosine distance is undefined for zero vectors
        for word in self._WORD.findall(text.lower()):
            if word in self._STOPWORDS:
                continue
            digest = hashlib.blake2b(word.encode(), digest_size=8).digest()
            position = int.from_bytes(digest[:4], "little") % self.dim
            vector[position] += 1.0 if digest[4] % 2 else -1.0
        return _normalize(vector)


class LocalEmbedder(EmbeddingProvider):
    """Runs a sentence-transformers model locally (CPU or Apple-silicon GPU)."""

    def __init__(self, model_name: str, dim: int, batch_size: int = 16):
        self.name = model_name
        self.dim = dim
        self.batch_size = batch_size
        self._model = None
        self._lock = threading.Lock()
        # E5 models are trained with these prefixes; BGE-M3 needs none
        is_e5 = "e5" in model_name.lower()
        self._query_prefix = "query: " if is_e5 else ""
        self._passage_prefix = "passage: " if is_e5 else ""

    def _load(self):
        with self._lock:
            if self._model is None:
                try:
                    from sentence_transformers import SentenceTransformer
                except ImportError as exc:
                    raise ConfigurationError(
                        "EMBEDDING_PROVIDER=local needs: pip install -r requirements-ml.txt"
                    ) from exc
                logger.info("Loading embedding model %s (first time downloads it)", self.name)
                model = SentenceTransformer(self.name)
                model_dim = model.get_embedding_dimension()
                if model_dim != self.dim:
                    raise ConfigurationError(
                        f"Embedding model {self.name} outputs {model_dim} dimensions but "
                        f"EMBEDDING_DIM is {self.dim}. Change one so they match."
                    )
                self._model = model
        return self._model

    def _encode(self, texts: list[str]) -> list[list[float]]:
        vectors = self._load().encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return vectors.tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._encode([self._passage_prefix + t for t in texts])

    def embed_query(self, text: str) -> list[float]:
        return self._encode([self._query_prefix + text])[0]


class OpenAICompatibleEmbedder(EmbeddingProvider):
    """Calls POST {base_url}/embeddings, retrying briefly on rate limits / server errors."""

    def __init__(self, base_url: str, api_key: str, model: str, dim: int, batch_size: int = 64):
        if not api_key:
            raise ConfigurationError("EMBEDDING_PROVIDER=openai_compatible needs an API key.")
        self.name = model
        self.dim = dim
        self.batch_size = batch_size
        self._url = base_url.rstrip("/") + "/embeddings"
        self._headers = {"Authorization": f"Bearer {api_key}"}

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for i in range(0, len(texts), self.batch_size):
            vectors.extend(self._request(texts[i : i + self.batch_size]))
        return vectors

    def _request(self, batch: list[str]) -> list[list[float]]:
        payload: dict = {"model": self.name, "input": batch}
        if self.name.startswith("text-embedding-3"):
            payload["dimensions"] = self.dim  # OpenAI v3 models can shorten their vectors
        for attempt in range(3):
            try:
                response = httpx.post(self._url, json=payload, headers=self._headers, timeout=60)
            except httpx.HTTPError as exc:
                error: str = type(exc).__name__
            else:
                if response.status_code == 200:
                    return self._parse(response.json(), len(batch))
                error = f"HTTP {response.status_code}"
                if response.status_code not in (429, 500, 502, 503, 504):
                    break
            time.sleep(2**attempt)
        logger.error("Embedding API failed: %s", error)
        raise ExternalServiceError("The embedding service is unavailable. Please try again.")

    def _parse(self, body: dict, expected: int) -> list[list[float]]:
        try:
            items = sorted(body["data"], key=lambda item: item["index"])
            vectors = [_normalize(item["embedding"]) for item in items]
        except (KeyError, TypeError) as exc:
            raise ExternalServiceError("The embedding service returned a malformed reply.") from exc
        if len(vectors) != expected or any(len(v) != self.dim for v in vectors):
            raise ConfigurationError(
                f"Embedding API returned vectors of the wrong size (expected {self.dim})."
            )
        return vectors


def build_embedder(settings: Settings) -> EmbeddingProvider:
    if settings.embedding_provider == "local":
        return LocalEmbedder(
            settings.embedding_model, settings.embedding_dim, settings.embedding_batch_size
        )
    if settings.embedding_provider == "openai_compatible":
        api_key = settings.embedding_api_key.get_secret_value()
        return OpenAICompatibleEmbedder(
            base_url=settings.embedding_base_url or settings.llm_base_url,
            api_key=api_key or settings.llm_api_key.get_secret_value(),
            model=settings.embedding_model,
            dim=settings.embedding_dim,
            batch_size=settings.embedding_batch_size,
        )
    return FakeEmbedder(settings.embedding_dim)


@lru_cache
def get_embedder() -> EmbeddingProvider:
    """One shared embedder per process (loading a local model is slow)."""
    return build_embedder(get_settings())
