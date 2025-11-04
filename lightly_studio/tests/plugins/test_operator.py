from lightly_studio.plugins.base_operator import EchoOperator


def test_echo_operator():
    operator = EchoOperator()
    assert operator.name == "Echo Operator"
    assert operator.description == "An operator that echoes the input parameters."
    assert operator.parameters == []

    result = operator.execute(
        session=None,
        dataset_id=None,
        parameters={"param1": "value1", "param2": 42},
    )
    assert result == {
        "success": True,
        "message": "Echoed parameters: {'param1': 'value1', 'param2': 42}, echoed dataset_id: None, echoed session: None",
    }
