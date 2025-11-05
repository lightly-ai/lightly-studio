from uuid import UUID

from sqlmodel import Session

from lightly_studio.plugins.base_operator import EchoOperator
from lightly_studio.plugins.parameter import StringParameter


def test_echo_operator() -> None:
    operator = EchoOperator()
    assert operator.name == "Echo Operator"
    assert operator.description == "An operator that echoes the input parameters."
    assert (
        operator.parameters[0].to_dict()
        == StringParameter(name="param1", description="A string parameter", required=True).to_dict()
    )

    session = Session()
    result = operator.execute(
        session=session,
        dataset_id=UUID(int=0),
        parameters={"param1": "value1"},
    )
    assert result == {
        "success": True,
        "message": f"value1, 00000000-0000-0000-0000-000000000000, {session}",
    }
