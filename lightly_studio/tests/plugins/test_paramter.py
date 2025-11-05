import pytest

from lightly_studio.plugins.parameter import (
    BoolParameter,
    FloatParameter,
    IntParameter,
    StringParameter,
)


def test_int_parameter() -> None:
    # valid minimal example
    param = IntParameter(name="test_int")
    assert param.name == "test_int"
    assert param.description == ""
    assert param.default is None
    assert param.required

    # valid full example
    param = IntParameter(name="test_int", description="abc", default=42, required=False)
    assert param.name == "test_int"
    assert param.description == "abc"
    assert param.default == 42
    assert not param.required

    # Validate to_dict
    assert param.to_dict() == {
        "name": "test_int",
        "type": "int",
        "description": "abc",
        "default": 42,
        "required": False,
    }

    # invalid default type string
    with pytest.raises(TypeError, match="Expected value of type 'int'"):
        _ = IntParameter(name="test_int", default="42")  # type: ignore [arg-type]

    # invalid default type boolean
    with pytest.raises(TypeError, match="Expected value of type 'int'"):
        _ = IntParameter(name="test_int", default=True)


def test_float_parameter() -> None:
    # valid minimal example
    param = FloatParameter(name="test_float")
    assert param.name == "test_float"
    assert param.description == ""
    assert param.default is None
    assert param.required

    # valid full example
    param = FloatParameter(name="test_float", description="abc", default=42.0, required=False)
    assert param.name == "test_float"
    assert param.description == "abc"
    assert param.default == 42.0
    assert not param.required

    # Validate to_dict
    assert param.to_dict() == {
        "name": "test_float",
        "type": "float",
        "description": "abc",
        "default": 42.0,
        "required": False,
    }

    # valid example int default
    param = FloatParameter(name="test_float", default=42)
    assert param.default == 42.0

    # invalid default type string
    with pytest.raises(TypeError, match="Expected value of type 'float'"):
        _ = FloatParameter(name="test_float", default="42") # type: ignore [arg-type]

    # invalid default type boolean
    with pytest.raises(TypeError, match="Expected value of type 'float'"):
        _ = FloatParameter(name="test_float", default=True)


def test_bool_parameter() -> None:
    # valid minimal example
    param = BoolParameter(name="test_bool")
    assert param.name == "test_bool"
    assert param.description == ""
    assert param.default is None
    assert param.required

    # valid full example
    param = BoolParameter(name="test_bool", description="abc", default=True, required=False)
    assert param.name == "test_bool"
    assert param.description == "abc"
    assert param.default
    assert not param.required

    # Validate to_dict
    assert param.to_dict() == {
        "name": "test_bool",
        "type": "bool",
        "description": "abc",
        "default": True,
        "required": False,
    }

    # invalid default type string
    with pytest.raises(TypeError, match="Expected value of type 'bool'"):
        _ = BoolParameter(name="test_bool", default=42) # type: ignore [arg-type]


def test_string_parameter() -> None:
    # valid minimal example
    param = StringParameter(name="test_string")
    assert param.name == "test_string"
    assert param.description == ""
    assert param.default is None
    assert param.required

    # valid full example
    param = StringParameter(name="test_string", description="abc", default="def", required=False)
    assert param.name == "test_string"
    assert param.description == "abc"
    assert param.default == "def"
    assert not param.required

    # Validate to_dict
    assert param.to_dict() == {
        "name": "test_string",
        "type": "str",
        "description": "abc",
        "default": "def",
        "required": False,
    }

    # invalid default type string
    with pytest.raises(TypeError, match="Expected value of type 'str'"):
        _ = StringParameter(name="test_string", default=42) # type: ignore [arg-type]
