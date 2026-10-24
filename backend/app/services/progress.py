"""Live progress of answers being written, for the chat page to poll (Phase 15).

Two parts per conversation: the agent's trace rows (stages and tool calls), and the live
answer (sources found so far, the draft as the model writes it, the checker's verdicts;
app/agents/live.py).

In memory, per process: the API runs as one process (uvicorn), and the trace and answer
are also stored with the run when it is done, so nothing is lost if this is cleared.
"""

import threading
import time

_KEEP_SECONDS = 15 * 60
_lock = threading.Lock()
_runs: dict[str, dict] = {}


def _entry(key: str) -> dict:
    entry = _runs.get(key)
    if entry is None or not entry["running"]:
        # A new answer: forget the previous one's trace and draft
        entry = _runs[key] = {
            "rows": [],
            "live": None,
            "running": True,
            "stop": False,
            "updated": 0.0,
        }
    entry["updated"] = time.time()
    return entry


def publish(key: str, rows: list[dict]) -> None:
    with _lock:
        _entry(key)["rows"] = rows
        _forget_old()


def publish_live(key: str, live: dict) -> None:
    with _lock:
        _entry(key)["live"] = live


def request_stop(key: str) -> bool:
    """Ask the answer being written in this conversation to stop; False if none is."""
    with _lock:
        entry = _runs.get(key)
        if entry is None or not entry["running"]:
            return False
        entry["stop"] = True
        return True


def stop_requested(key: str) -> bool:
    with _lock:
        entry = _runs.get(key)
        return bool(entry and entry["running"] and entry.get("stop"))


def finish(key: str) -> None:
    with _lock:
        if key in _runs:
            _runs[key]["running"] = False
            _runs[key]["updated"] = time.time()


def get(key: str) -> dict:
    with _lock:
        entry = _runs.get(key)
        if entry is None:
            return {"running": False, "steps": [], "live": None}
        return {
            "running": entry["running"],
            "steps": [dict(row) for row in entry["rows"]],
            "live": entry["live"],
        }


def _forget_old() -> None:
    cutoff = time.time() - _KEEP_SECONDS
    for key in [k for k, v in _runs.items() if v["updated"] < cutoff]:
        del _runs[key]
