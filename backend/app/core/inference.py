"""One lock around every local model call (embeddings, reranker, NLI).

Observed (2026-10-04): two requests embedding at the same time (a patent import while
another was indexing) crashed the whole API process inside Apple's Metal driver
("failed assertion _status < MTLCommandBufferStatusCommitted"). PyTorch's MPS backend is
not safe for concurrent use from several threads, and FastAPI runs sync endpoints in a
thread pool. Serialising inference costs little here (one GPU, one user at a time) and
turns a crash into a short wait.
"""

import threading

INFERENCE_LOCK = threading.RLock()
