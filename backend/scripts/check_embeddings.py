"""Sanity-check the configured embedding provider on a few patent-style sentences.

    cd backend && EMBEDDING_PROVIDER=local .venv/bin/python -m scripts.check_embeddings

A good model should rate the paraphrase pair far above the unrelated pair.
"""

import time

from app.core.config import get_settings
from app.rag.embeddings import build_embedder

PAIRS = [
    (
        "paraphrase",
        "wireless charging pad for a phone",
        "inductive power transfer to a mobile device",
    ),
    ("related", "battery cell temperature sensor", "thermistor bonded to a lithium-ion cell"),
    ("unrelated", "wireless charging pad for a phone", "method of brewing coffee with steam"),
]


def main() -> None:
    settings = get_settings()
    embedder = build_embedder(settings)
    print(f"provider={settings.embedding_provider} model={embedder.name} dim={embedder.dim}")

    started = time.perf_counter()
    embedder.embed_query("warm-up")  # loads / downloads the model
    print(f"model ready in {time.perf_counter() - started:.1f}s")

    for label, a, b in PAIRS:
        va = embedder.embed_query(a)
        vb = embedder.embed_documents([b])[0]
        similarity = sum(x * y for x, y in zip(va, vb, strict=True))
        print(f"{label:<11} cosine={similarity:.3f}   {a!r} vs {b!r}")

    texts = ["A coolant pump circulates water-glycol through cooling channels."] * 32
    started = time.perf_counter()
    embedder.embed_documents(texts)
    print(f"throughput: {len(texts) / (time.perf_counter() - started):.1f} passages/s")


if __name__ == "__main__":
    main()
