"""HTTP middleware: assigns a request ID and logs one summary line per request."""

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import request_id_var

logger = logging.getLogger("app.request")

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Reuse a client-supplied ID only if it is short and safe; otherwise generate one
        incoming = request.headers.get(REQUEST_ID_HEADER, "")
        request_id = incoming if incoming.isalnum() and len(incoming) <= 64 else uuid.uuid4().hex
        token = request_id_var.set(request_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
            response.headers[REQUEST_ID_HEADER] = request_id
            logger.info(
                "%s %s -> %s (%.1f ms)",
                request.method,
                request.url.path,
                response.status_code,
                (time.perf_counter() - start) * 1000,
            )
            return response
        except Exception:
            logger.exception("%s %s -> unhandled error", request.method, request.url.path)
            raise
        finally:
            request_id_var.reset(token)
