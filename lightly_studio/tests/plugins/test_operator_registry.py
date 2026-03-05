from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlmodel import Session

from lightly_studio.plugins.base_operator import BaseOperator, OperatorResult, OperatorStatus
from lightly_studio.plugins.operator_context import ExecutionContext, OperatorScope
from lightly_studio.plugins.operator_registry import OperatorRegistry
from lightly_studio.plugins.parameter import BaseParameter, BoolParameter, StringParameter
from tests.helpers_resolvers import create_collection


def test_operator_registry__empty() -> None:
    # Check if operator is already registered
    operator_registry = OperatorRegistry()
    assert operator_registry.get_by_id("some_id") is None


def test_operator_registry__dummy_operators(db_session: Session) -> None:
    # Create a local registry and register a test operator
    operator_registry = OperatorRegistry()
    input_operator = TestOperator()
    operator_registry.register(operator=input_operator)

    # Validate that the registry returns the expected values
    operator_info_list = operator_registry.get_all_metadata()
    assert len(operator_info_list) == 1
    assert operator_info_list[0].name == "test operator"

    # Validate and Execute the test operator retrieved from the registry
    operator = operator_registry.get_by_id(operator_id=operator_info_list[0].operator_id)
    assert operator == input_operator

    collection = create_collection(session=db_session)
    context = ExecutionContext(collection_id=collection.collection_id, context_filter=None)
    result = operator.execute(
        session=db_session,
        context=context,
        parameters={"test flag": True, "test str": "test value"},
    )

    assert result.success
    assert result.message == "test value " + str(db_session) + " " + str(collection.collection_id)

    # Register another operator and make sure we have two now.
    operator_registry.register(TestOperator())
    operator_info_list = operator_registry.get_all_metadata()
    assert len(operator_info_list) == 2


def test_operator_registry__startup_all_sets_ready() -> None:
    operator = TestOperator()
    assert operator.status == OperatorStatus.PENDING

    registry = OperatorRegistry()
    registry.register(operator)
    registry.startup_all()

    assert operator.status == OperatorStatus.READY


def test_operator_registry__shutdown_all_sets_stopped() -> None:
    operator = TestOperator()
    registry = OperatorRegistry()
    registry.register(operator)
    registry.startup_all()
    registry.shutdown_all()

    assert operator.status == OperatorStatus.STOPPED


def test_operator_registry__startup_all_sets_error_on_failure() -> None:
    operator = FailingStartupOperator()
    registry = OperatorRegistry()
    registry.register(operator)
    registry.startup_all()

    assert operator.status == OperatorStatus.ERROR


def test_operator_registry__startup_all_continues_after_failure() -> None:
    failing = FailingStartupOperator()
    healthy = TestOperator()
    registry = OperatorRegistry()
    registry.register(failing)
    registry.register(healthy)
    registry.startup_all()

    assert failing.status == OperatorStatus.ERROR
    assert healthy.status == OperatorStatus.READY


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


@dataclass
class FailingStartupOperator(BaseOperator):
    name: str = "failing operator"
    description: str = "always raises during startup"

    @property
    def parameters(self) -> list[BaseParameter]:
        """Return the list of parameters this operator expects."""
        return []

    @property
    def supported_scopes(self) -> list[OperatorScope]:
        """Return the list of scopes this operator can be triggered from."""
        return [OperatorScope.ROOT]

    def startup(self) -> None:
        """Raise to simulate a broken operator."""
        raise RuntimeError("startup failed")

    def execute(
        self,
        *,
        session: Session,
        context: ExecutionContext,
        parameters: dict[str, Any],
    ) -> OperatorResult:
        """Not expected to be called in tests."""
        raise NotImplementedError  # pragma: no cover
