from __future__ import annotations

from sqlmodel import Session

from lightly_studio.plugins.operator_registry import OperatorRegistry
from tests.helpers_resolvers import create_dataset
from tests.plugins.helpers import TestOperator


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

    dataset = create_dataset(session=db_session)
    result = operator.execute(
        session=db_session,
        dataset_id=dataset.dataset_id,
        parameters={"test flag": True, "test str": "test value"},
    )

    assert result.success
    assert result.message == "test value " + str(db_session) + " " + str(dataset.dataset_id)

    # Register another operator and make sure we have two now.
    operator_registry.register(TestOperator())
