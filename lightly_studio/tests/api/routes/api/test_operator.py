from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

import lightly_studio.api.routes.api.operator as operator_routes_module
import lightly_studio.plugins.operator_registry as operator_registry_module
from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_OK,
)
from lightly_studio.plugins.base_operator import BaseOperator, OperatorResult
from lightly_studio.plugins.operator_context import ExecutionContext, OperatorScope
from lightly_studio.plugins.operator_registry import OperatorRegistry
from lightly_studio.plugins.parameter import BaseParameter, BoolParameter, StringParameter


@pytest.fixture
def isolated_operator_registry() -> Generator[OperatorRegistry, None, None]:
    original_registry = operator_registry_module.operator_registry
    registry = OperatorRegistry()
    operator_registry_module.operator_registry = registry
    operator_routes_module.operator_registry = registry  # type: ignore [attr-defined]
    try:
        yield registry
    finally:
        operator_registry_module.operator_registry = original_registry
        operator_routes_module.operator_registry = original_registry  # type: ignore [attr-defined]


def test_get_operators__empty(
    test_client: TestClient,
    isolated_operator_registry: OperatorRegistry,
) -> None:
    _ = isolated_operator_registry  # ensure fixture is used for mypy
    response = test_client.get("/api/operators")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == []


def test_get_operators__multiple(
    test_client: TestClient,
    isolated_operator_registry: OperatorRegistry,
) -> None:
    isolated_operator_registry.register(TestOperator(name="Op A"))
    isolated_operator_registry.register(TestOperator(name="Op B"))

    response = test_client.get("/api/operators")

    assert response.status_code == HTTP_STATUS_OK
    payload = response.json()
    assert {payload[0]["name"], payload[1]["name"]} == {"Op A", "Op B"}
    assert len(payload) == 2


def test_get_operator_parameters__operator_not_found(
    test_client: TestClient,
    isolated_operator_registry: OperatorRegistry,
) -> None:
    _ = isolated_operator_registry  # ensure fixture is used for mypy
    response = test_client.get("/api/operators/unknown-id/parameters")

    assert response.status_code == HTTP_STATUS_NOT_FOUND
    assert response.json() == {"detail": "Operator 'unknown-id' not found"}


def test_get_operator_parameters__no_parameters(
    test_client: TestClient,
    isolated_operator_registry: OperatorRegistry,
) -> None:
    # Add an operator with empty parameters:
    isolated_operator_registry.register(EmptyParamsOperator(name="empty"))

    operator_id = _get_operator_id_by_name(isolated_operator_registry, "empty")

    response = test_client.get(f"/api/operators/{operator_id}/parameters")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == []


def test_get_operator_parameters__multiple_parameters(
    test_client: TestClient,
    isolated_operator_registry: OperatorRegistry,
) -> None:
    # Add an operator with multiple parameters:
    # - BoolParameter(name="test flag", required=True)
    # - StringParameter(name="test str", required=True)
    isolated_operator_registry.register(TestOperator(name="multi"))

    operator_id = _get_operator_id_by_name(isolated_operator_registry, "multi")

    response = test_client.get(f"/api/operators/{operator_id}/parameters")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == [
        {
            "name": "test flag",
            "description": "",
            "default": None,
            "required": True,
            "param_type": "bool",
        },
        {
            "name": "test str",
            "description": "",
            "default": None,
            "required": True,
            "param_type": "str",
        },
    ]


def test_execute_operator__operator_not_found(
    test_client: TestClient,
    collection_id: UUID,
    isolated_operator_registry: OperatorRegistry,
) -> None:
    _ = isolated_operator_registry  # ensure fixture is used for mypy
    unknown_operator_id = "missing"

    response = test_client.post(
        f"/api/operators/collections/{collection_id}/{unknown_operator_id}/execute",
        json={"parameters": {"x": 1}},
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND
    assert response.json() == {"detail": "Operator 'missing' not found"}


def test_execute_operator__successful(
    test_client: TestClient,
    db_session: Session,
    collection_id: UUID,
    isolated_operator_registry: OperatorRegistry,
) -> None:
    operator = TestOperator(name="success")
    isolated_operator_registry.register(operator)
    operator_id = _get_operator_id_by_name(isolated_operator_registry, "success")

    response = test_client.post(
        f"/api/operators/collections/{collection_id}/{operator_id}/execute",
        json={"parameters": {"test flag": True, "test str": "Some text"}},
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {
        "success": True,
        "message": "Some text " + str(db_session) + " " + str(collection_id),
    }


def _get_operator_id_by_name(registry: OperatorRegistry, target_name: str) -> str:
    for metadata in registry.get_all_metadata():
        if metadata.name == target_name:
            return metadata.operator_id
    raise AssertionError(f"Operator named '{target_name}' not found in registry metadata.")


@dataclass
class TestOperator(BaseOperator):
    name: str = "test operator"
    description: str = "used to test the operator and registry system"

    @property
    def parameters(self) -> list[BaseParameter]:
        """Return the list of parameters this operator expects."""
        return [
            BoolParameter(name="test flag", required=True),
            StringParameter(name="test str", required=True),
        ]

    @property
    def supported_scopes(self) -> list[OperatorScope]:
        """Return the list of scopes this operator can be triggered from."""
        return [OperatorScope.ROOT]

    def execute(
        self,
        *,
        session: Session,
        context: ExecutionContext,
        parameters: dict[str, Any],
    ) -> OperatorResult:
        """Execute the operator with the given parameters.

        Args:
            session: Database session.
            context: Execution context containing collection_id and optional filter.
            parameters: Parameters passed to the operator.

        Returns:
            Dictionary with 'success' (bool) and 'message' (str) keys.
        """
        return OperatorResult(
            success=bool(parameters.get("test flag")),
            message=str(parameters.get("test str"))
            + " "
            + str(session)
            + " "
            + str(context.collection_id),
        )


class EmptyParamsOperator(TestOperator):
    @property
    def parameters(self) -> list[BaseParameter]:
        return []
