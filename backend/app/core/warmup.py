"""Load the local models when the API starts, not on the first question.

Observed (2026-10-11): the first question after `make demo` waited about 20 s while the
embedding and NLI models loaded, and the user took the app for unresponsive. Loading runs
in a background thread, so the API is reachable at once; a question asked meanwhile simply
waits for the model as before.
"""

import logging
import threading
import time

from app.core.config import Settings

logger = logging.getLogger(__name__)


def warm_up(settings: Settings) -> None:
    started = time.perf_counter()
    try:
        if settings.embedding_provider == "local":
            from app.rag.embeddings import get_embedder

            get_embedder().embed_query("warm up")
        if settings.verifier_method in ("auto", "nli", "nli_lexical", "nli_llm"):
            from app.verification.verifiers import _shared_nli

            _shared_nli(settings.verifier_nli_model).judge(["warm up"], [["warm up"]])
        if settings.reranker_enabled and settings.reranker_provider == "local":
            from app.rag.reranker import get_reranker_for

            reranker = get_reranker_for(settings)
            if reranker is not None:
                reranker.score("warm up", ["warm up"])
    except Exception:  # noqa: BLE001 - the first question will load (and report) it instead
        logger.warning("Model warm-up failed", exc_info=True)
        return
    logger.info("Models ready (warm-up took %.1f s)", time.perf_counter() - started)


def start_warm_up(settings: Settings) -> threading.Thread | None:
    """Only for real local models; tests and the fake providers need nothing."""
    if settings.embedding_provider != "local":
        return None
    thread = threading.Thread(target=warm_up, args=(settings,), name="model-warm-up", daemon=True)
    thread.start()
    return thread
