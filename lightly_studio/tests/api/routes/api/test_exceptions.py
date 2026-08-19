"""Tests for exception handlers."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.exceptions import ResponseValidationError
from fastapi.testclient import TestClient
from sqlalchemy.exc import DataError, IntegrityError, OperationalError

from lightly_studio.api.routes.api.exceptions import register_exception_handlers
from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_REQUEST,
    HTTP_STATUS_CONFLICT,
    HTTP_STATUS_INTERNAL_SERVER_ERROR,
)


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
