"""Local model calls never run concurrently (a Metal/MPS crash on 2026-10-04)."""

import threading
import time

from app.rag.embeddings import LocalEmbedder


class OverlapRecorder:
    def __init__(self):
        self.active = 0
        self.max_active = 0
        self.guard = threading.Lock()

    def encode(self, texts, **kwargs):
        import numpy as np

        with self.guard:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        time.sleep(0.05)
        with self.guard:
            self.active -= 1
        return np.zeros((len(texts), 4))


def test_concurrent_embedding_calls_are_serialised():
    model = OverlapRecorder()
    embedder = LocalEmbedder.__new__(LocalEmbedder)
    embedder.batch_size = 8
    embedder._passage_prefix = embedder._query_prefix = ""
    embedder._load = lambda: model
    errors = []

    def work():
        try:
            embedder.embed_documents(["a", "b"])
        except Exception as exc:  # noqa: BLE001 - surfaced by the assert below
            errors.append(exc)

    threads = [threading.Thread(target=work) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert model.max_active == 1  # never two model calls at once
