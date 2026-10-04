"""Application errors and the handlers that turn them into consistent JSON responses.

Every error response has the same shape, which makes the frontend simpler:

    {"error": {"code": "unsupported_file_type", "message": "...", "request_id": "..."}}

Internal details (stack traces, SQL, API keys) are logged server-side only and
never sent to the client.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import request_id_var

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base class for errors we expect and can explain to the user."""

    status_code = 400
    code = "bad_request"

    def __init__(self, message: str, *, code: str | None = None, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ValidationFailedError(AppError):
    status_code = 422
    code = "validation_failed"


class ExternalServiceError(AppError):
    """An upstream dependency (LLM, embedding API, patent API) failed or timed out."""

    status_code = 502
    code = "external_service_error"


class ServiceUnavailableError(AppError):
    status_code = 503
    code = "service_unavailable"


class ConfigurationError(AppError):
    """The server is misconfigured (e.g. embedding size does not match the database)."""

    status_code = 500
    code = "configuration_error"


# --- Document upload / ingestion ---


class UnsupportedFileError(AppError):
    status_code = 415
    code = "unsupported_file_type"


class FileTooLargeError(AppError):
    status_code = 413
    code = "file_too_large"


class InvalidDocumentError(AppError):
    """The file has the right extension but cannot be read (corrupt, encrypted, wrong content)."""

    status_code = 422
    code = "invalid_document"


class EmptyDocumentError(AppError):
    status_code = 422
    code = "empty_document"


def _error_body(code: str, message: str, details: object = None) -> dict:
    body: dict = {"code": code, "message": message, "request_id": request_id_var.get()}
    if details is not None:
        body["details"] = details
    return {"error": body}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        logger.warning("AppError %s: %s", exc.code, exc.message)
        return JSONResponse(status_code=exc.status_code, content=_error_body(exc.code, exc.message))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"field": ".".join(str(p) for p in err["loc"]), "message": err["msg"]}
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=_error_body("validation_failed", "The request was invalid.", details),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code, content=_error_body("http_error", str(exc.detail))
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error: %s", type(exc).__name__)
        return JSONResponse(
            status_code=500,
            content=_error_body(
                "internal_error", "An unexpected error occurred. Please try again."
            ),
        )
