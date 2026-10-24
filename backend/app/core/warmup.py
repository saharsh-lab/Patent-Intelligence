"""Load the local models when the API starts, not on the first question.

Observed (2026-10-11): the first question after `make demo` waited about 20 s while the
embedding and NLI models loaded, and the user took the app for unresponsive. Loading runs
in a background thread, so the API is reachable at once; a question asked meanwhile simply
waits for the model as before.
"""

import logging
import threading
import time
from urllib.parse import urlparse

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


def local_llm(settings: Settings) -> bool:
    host = urlparse(settings.llm_base_url).hostname or ""
    return settings.llm_provider == "openai_compatible" and host in (
        "localhost",
        "127.0.0.1",
        "host.docker.internal",
    )


def keep_warm(settings: Settings, stop: threading.Event) -> None:
    """Keep the local LLM loaded. Ollama unloads a model after 5 idle minutes, and reloading
    the 5 GB Qwen3-8B made the first question after a pause wait several seconds more
    (2026-10-22). A one-token request every few minutes, and one at start-up, avoids that."""
    from app.llm.providers import ChatMessage, build_llm

    llm = build_llm(settings)
    interval = settings.llm_keep_warm_minutes * 60
    while True:
        try:
            llm.complete([ChatMessage("user", "ok")], temperature=0.0, max_tokens=1)
        except Exception:  # noqa: BLE001 - Ollama closed or busy: try again next time
            logger.info("Keep-warm request to the LLM failed")
        if stop.wait(interval):
            return


def start_keep_warm(settings: Settings) -> threading.Event | None:
    if not local_llm(settings) or settings.llm_keep_warm_minutes <= 0:
        return None
    stop = threading.Event()
    threading.Thread(
        target=keep_warm, args=(settings, stop), name="llm-keep-warm", daemon=True
    ).start()
    return stop


def start_warm_up(settings: Settings) -> threading.Thread | None:
    """Only for real local models; tests and the fake providers need nothing."""
    if settings.embedding_provider != "local":
        return None
    thread = threading.Thread(target=warm_up, args=(settings,), name="model-warm-up", daemon=True)
    thread.start()
    return thread
