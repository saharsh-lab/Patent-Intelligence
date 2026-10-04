"""Logging setup.

Every log line carries the current request ID so that all lines belonging to
one user request (API call -> agent run -> tool calls) can be grouped together.
A redaction filter masks anything that looks like a secret before it is written.
"""

import logging
import re
from contextvars import ContextVar

# Holds the ID of the request currently being handled (set by RequestIdMiddleware)
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

_SECRET_PATTERNS = [
    # Bearer tokens (must run before the key=value rule, which would only mask 'Bearer')
    re.compile(r"(?i)(bearer\s+)()()[A-Za-z0-9._\-]+"),
    # key=value / key: value pairs whose key name suggests a secret
    re.compile(
        r"(?i)\b(api[_-]?key|secret|password|token|authorization)\b(\s*[=:]\s*)(\"?)[^\s\",]+"
    ),
    # OpenAI-style keys
    re.compile(r"()()()\bsk-[A-Za-z0-9_\-]{8,}"),
    # Passwords embedded in connection URLs: scheme://user:password@host
    re.compile(r"(://[^:/\s]+)(:)()[^@\s]+(?=@)"),
]


def redact(text: str) -> str:
    """Replace secret-looking substrings with '***'."""
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}***", text)
    return text


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return redact(super().format(record))


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(
        RedactingFormatter("%(asctime)s %(levelname)-7s [%(request_id)s] %(name)s: %(message)s")
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    # Uvicorn's own access log duplicates our request log line
    logging.getLogger("uvicorn.access").disabled = True
