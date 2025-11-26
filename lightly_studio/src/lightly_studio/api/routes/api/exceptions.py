"""This module contains the FastAPI app configuration."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DataError, IntegrityError, OperationalError

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_REQUEST,
    HTTP_STATUS_CONFLICT,
    HTTP_STATUS_INTERNAL_SERVER_ERROR,
    HTTP_STATUS_UNPROCESSABLE_ENTITY,
)

# Set up logger for error handling
logger = logging.getLogger("lightly_studio.api.exceptions")


def _log_error_details(
    exc: Exception,
    status_code: int,
) -> None:
    """Log detailed error information with request context."""
    # Log the error with different levels based on status code
    logger.error(f"Server Error {status_code}: {exc}")


def register_exception_handlers(app: FastAPI) -> None:
    """Register exception handlers for the FastAPI app."""

    @app.exception_handler(IntegrityError)
    async def _integrity_error_handler(_request: Request, _exc: IntegrityError) -> JSONResponse:
        """Handle database integrity errors."""
        _log_error_details(
            exc=_exc,
            status_code=HTTP_STATUS_CONFLICT,
        )

        return JSONResponse(
            status_code=HTTP_STATUS_CONFLICT,
            content={"error": _exc.statement or "Database constraint violated."},
        )

    @app.exception_handler(OperationalError)
    async def _operational_error_handler(_request: Request, _exc: OperationalError) -> JSONResponse:
        """Handle database operational errors."""
        _log_error_details(
            exc=_exc,
            status_code=HTTP_STATUS_INTERNAL_SERVER_ERROR,
        )
        return JSONResponse(
            status_code=HTTP_STATUS_INTERNAL_SERVER_ERROR,
            content={"error": _exc.statement or "Database operation failed."},
        )

    @app.exception_handler(DataError)
    async def _data_error_handler(_request: Request, _exc: DataError) -> JSONResponse:
        """Handle database data errors."""
        _log_error_details(
            exc=_exc,
            status_code=HTTP_STATUS_BAD_REQUEST,
        )
        return JSONResponse(
            status_code=HTTP_STATUS_BAD_REQUEST,
            content={"error": _exc.statement or "Invalid response."},
        )

    @app.exception_handler(ResponseValidationError)
    async def _data_validation_error_handler(
        _request: Request, _exc: ResponseValidationError
    ) -> JSONResponse:
        """Handle database data errors."""
        error_details = _exc.errors()
        if error_details:
            detail = error_details[0].get("msg", "Invalid data provided.")
        else:
            detail = "Invalid data provided."

        _log_error_details(
            exc=_exc,
            status_code=HTTP_STATUS_BAD_REQUEST,
        )

        return JSONResponse(status_code=HTTP_STATUS_BAD_REQUEST, content={"error": detail})

    @app.exception_handler(ValueError)
    async def _value_error_handler(_request: Request, _exc: ValueError) -> JSONResponse:
        """Handle value errors."""
        _log_error_details(
            exc=_exc,
            status_code=HTTP_STATUS_INTERNAL_SERVER_ERROR,
        )
        return JSONResponse(status_code=HTTP_STATUS_BAD_REQUEST, content={"error": str(_exc)})

    @app.exception_handler(RequestValidationError)
    async def _request_validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        body = (await request.body()).decode("utf-8", errors="replace")
        logger.warning(
            "Request validation error on %s?%s | errors=%s | body=%s",
            request.url.path,
            request.url.query,
            exc.errors(),
            body[:500],  # don't log huge bodies
        )
        return JSONResponse(
            status_code=HTTP_STATUS_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors()},
        )
