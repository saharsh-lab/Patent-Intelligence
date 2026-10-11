"""Live progress of answers being written, for the chat page to poll (Phase 15).

In memory, per process: the API runs as one process (uvicorn), and the trace is also
stored with the answer when it is done, so nothing is lost if this is cleared.
"""

import threading
import time

_KEEP_SECONDS = 15 * 60
_lock = threading.Lock()
_runs: dict[str, dict] = {}


def publish(key: str, rows: list[dict]) -> None:
    with _lock:
        _runs[key] = {"rows": rows, "running": True, "updated": time.time()}
        _forget_old()


def finish(key: str) -> None:
    with _lock:
        if key in _runs:
            _runs[key]["running"] = False
            _runs[key]["updated"] = time.time()


def get(key: str) -> dict:
    with _lock:
        entry = _runs.get(key)
        return (
            {"running": False, "steps": []}
            if entry is None
            else {
                "running": entry["running"],
                "steps": [dict(row) for row in entry["rows"]],
            }
        )


def _forget_old() -> None:
    cutoff = time.time() - _KEEP_SECONDS
    for key in [k for k, v in _runs.items() if v["updated"] < cutoff]:
        del _runs[key]
