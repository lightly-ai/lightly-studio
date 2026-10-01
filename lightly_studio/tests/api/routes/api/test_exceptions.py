"""Tests for exception handlers."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlalchemy.exc import DataError, IntegrityError, OperationalError

from lightly_studio.api.routes.api.exceptions import register_exception_handlers
from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_REQUEST,
    HTTP_STATUS_CONFLICT,
    HTTP_STATUS_INTERNAL_SERVER_ERROR,
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_UNPROCESSABLE_ENTITY,
)
from lightly_studio.errors import NotFoundError


@pytest.fixture
def app_with_exception_handlers() -> FastAPI:
    """Test app."""
    app = FastAPI()
    register_exception_handlers(app)
    return app


@pytest.fixture
def client(app_with_exception_handlers: FastAPI) -> TestClient:
    """Test client."""
    return TestClient(app_with_exception_handlers)


def test_register_exception_handlers__integrity_error_handler(
    app_with_exception_handlers: FastAPI, client: TestClient
) -> None:
    """Test the integrity error handler."""
    msg = "Some integrity error."
    path = "/test-integrity"

    # Create a test endpoint that raises IntegrityError
    @app_with_exception_handlers.get(path)
    async def test_integrity_error() -> None:
        raise IntegrityError(msg, "test", BaseException("test"))

    response = client.get(path)

    assert response.status_code == HTTP_STATUS_CONFLICT
    assert response.json() == {"error": msg}


def test_register_exception_handlers__operational_error_handler(
    app_with_exception_handlers: FastAPI, client: TestClient
) -> None:
    """Test the operational error handler."""
    msg = "Some operational error."
    path = "/test-operational-error"

    # Create a test endpoint that raises OperationalError
    @app_with_exception_handlers.get(path)
    async def test_operational_error() -> None:
        raise OperationalError(msg, "test", BaseException("test."))

    response = client.get(path)

    assert response.status_code == HTTP_STATUS_INTERNAL_SERVER_ERROR
    assert response.json() == {"error": msg}


def test_register_exception_handlers__data_error_handler(
    app_with_exception_handlers: FastAPI, client: TestClient
) -> None:
    """Test the data error handler."""
    msg = "Some data error."
    path = "/test-data-error"

    # Create a test endpoint that raises DataError
    @app_with_exception_handlers.get(path)
    async def test_data_error() -> None:
        raise DataError(msg, "test", BaseException("test."))

    response = client.get(path)

    assert response.status_code == HTTP_STATUS_BAD_REQUEST
    assert response.json() == {"error": msg}


def test_register_exception_handlers__validation_error_handler(
    app_with_exception_handlers: FastAPI, client: TestClient
) -> None:
    """Test the validation error handler."""
    msg = "Some validation error."
    path = "/test-validation-error"

    # Create a test endpoint that raises DataError
    @app_with_exception_handlers.get(path)
    async def test_validation_error() -> None:
        validation_errors = [
            {
                "type": "value_error",
                "loc": ("body", "field"),
                "msg": msg,
                "input": None,
            }
        ]
        raise ResponseValidationError(validation_errors)

    response = client.get(path)

    assert response.status_code == HTTP_STATUS_BAD_REQUEST
    assert response.json() == {"error": msg}


def test_register_exception_handlers__value_error_handler(
    app_with_exception_handlers: FastAPI, client: TestClient
) -> None:
    """Test the value error handler."""
    msg = "Some value error."
    path = "/test-value-error"

    # Create a test endpoint that raises ValueError
    @app_with_exception_handlers.get(path)
    async def test_value_error() -> None:
        raise ValueError(msg)

    response = client.get(path)

    assert response.status_code == HTTP_STATUS_BAD_REQUEST
    assert response.json() == {"error": msg}


def test_register_exception_handlers__request_validation_error_handler_reports_error(
    app_with_exception_handlers: FastAPI, client: TestClient, mocker: MockerFixture
) -> None:
    """Test the request validation error handler reports the error."""
    path = "/test-request-validation-error"
    mock_report_error = mocker.patch("lightly_studio.api.routes.api.exceptions._report_error")

    @app_with_exception_handlers.get(path)
    async def test_request_validation_error(value: int) -> None:
        del value

    response = client.get(path, params={"value": "invalid"})

    assert response.status_code == HTTP_STATUS_UNPROCESSABLE_ENTITY
    assert response.json()["detail"][0]["loc"] == ["query", "value"]
    assert response.json()["detail"][0]["msg"] == (
        "Input should be a valid integer, unable to parse string as an integer"
    )
    mock_report_error.assert_called_once()
    report_error_kwargs = mock_report_error.call_args.kwargs
    assert isinstance(report_error_kwargs["exc"], RequestValidationError)
    assert report_error_kwargs["status_code"] == HTTP_STATUS_UNPROCESSABLE_ENTITY


def test_register_exception_handlers__not_found_error_handler_reports_error(
    app_with_exception_handlers: FastAPI, client: TestClient, mocker: MockerFixture
) -> None:
    """Test the not-found error handler reports the error."""
    msg = "Resource was not found."
    path = "/test-not-found-error"
    mock_report_error = mocker.patch("lightly_studio.api.routes.api.exceptions._report_error")

    @app_with_exception_handlers.get(path)
    async def test_not_found_error() -> None:
        raise NotFoundError(msg)

    response = client.get(path)

    assert response.status_code == HTTP_STATUS_NOT_FOUND
    assert response.json() == {"error": msg}
    mock_report_error.assert_called_once()
    report_error_kwargs = mock_report_error.call_args.kwargs
    assert isinstance(report_error_kwargs["exc"], NotFoundError)
    assert report_error_kwargs["status_code"] == HTTP_STATUS_NOT_FOUND


def test_register_exception_handlers__unhandled_exception_handler(
    app_with_exception_handlers: FastAPI, mocker: MockerFixture
) -> None:
    """Test the catch-all exception handler."""
    path = "/test-unhandled-exception"
    mock_track = mocker.patch("lightly_studio.analytics.tracking.track_exception")
    # raise_server_exceptions=False so TestClient returns the 500 response instead of
    # re-raising the RuntimeError that ServerErrorMiddleware passes through.
    client = TestClient(app_with_exception_handlers, raise_server_exceptions=False)

    @app_with_exception_handlers.get(path)
    async def test_unhandled_exception() -> None:
        raise RuntimeError("Something unexpected.")

    response = client.get(path)

    assert response.status_code == HTTP_STATUS_INTERNAL_SERVER_ERROR
    assert response.json() == {"error": "Internal server error."}
    mock_track.assert_called_once()
