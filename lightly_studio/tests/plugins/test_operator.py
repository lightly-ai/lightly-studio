from dataclasses import asdict
from uuid import UUID

from sqlmodel import Session

from lightly_studio.plugins.base_operator import EchoOperator
from lightly_studio.plugins.parameter import StringParameter


def test_echo_operator(test_db: Session) -> None:
    operator = EchoOperator()
    assert operator.name == "Echo Operator"
    assert operator.description == "An operator that echoes the input parameters."
    assert asdict(operator.parameters[0]) == asdict(
        StringParameter(name="param1", description="A string parameter", required=True)
    )

    result = operator.execute(
        session=test_db,
        dataset_id=UUID(int=0),
        parameters={"param1": "value1"},
    )
    assert result == {
        "success": True,
        "message": f"value1, 00000000-0000-0000-0000-000000000000, {test_db}",
    }
