from dataclasses import asdict
from typing import Any
from uuid import UUID

from sqlmodel import Session

from lightly_studio.plugins.base_operator import BaseOperator, OperatorResult
from lightly_studio.plugins.parameter import BaseParameter, StringParameter


class _TestOperator(BaseOperator):
    """Concrete operator used for verifying the BaseOperator contract."""

    def __init__(self) -> None:
        self._executed_with: tuple[Session, UUID, dict[str, Any]] | None = None

    @property
    def name(self) -> str:
        return "Test Operator"

    @property
    def description(self) -> str:
        return "Used to test BaseOperator."

    @property
    def parameters(self) -> list[BaseParameter]:
        return [
            StringParameter(name="param1", description="A string parameter", required=True),
        ]

    def execute(
        self,
        *,
        session: Session,
        dataset_id: UUID,
        parameters: dict[str, Any],
    ) -> OperatorResult:
        self._executed_with = (session, dataset_id, parameters)
        return {"success": True, "message": parameters["param1"]}


def test_base_operator_contract(test_db: Session) -> None:
    operator = _TestOperator()

    assert operator.name == "Test Operator"
    assert operator.description == "Used to test BaseOperator."
    assert asdict(operator.parameters[0]) == asdict(
        StringParameter(name="param1", description="A string parameter", required=True)
    )

    parameters = {"param1": "value1"}
    dataset_id = UUID(int=0)
    result = operator.execute(session=test_db, dataset_id=dataset_id, parameters=parameters)

    assert result == {"success": True, "message": "value1"}
    assert operator._executed_with == (test_db, dataset_id, parameters)
