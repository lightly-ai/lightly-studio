from dataclasses import asdict

import pytest

from lightly_studio.plugins.parameter import (
    FloatParameter,
    IntParameter,
)


def test_parameters() -> None:
    # Test dict conversion yield the expected format
    param = IntParameter(name="test_int", description="abc", default=42, required=False)

    assert asdict(param) == {
        "name": "test_int",
        "description": "abc",
        "default": 42,
        "required": False,
        "param_type": "int",
    }


def test_builtin_parameters() -> None:
    # Test some variants as representative for all built-in parameters
    _ = IntParameter(name="test_int")
    _ = IntParameter(name="test_int", default=42)
    _ = IntParameter(name="test_int", default=True)
    _ = FloatParameter(name="test_float", default=42.0)

    # invalid default types
    with pytest.raises(TypeError, match="Expected value of type 'int'"):
        _ = IntParameter(name="test_int", default="42")
    with pytest.raises(TypeError, match="Expected value of type 'int'"):
        _ = IntParameter(name="test_int", default=42.0)
    with pytest.raises(TypeError, match="Expected value of type 'float'"):
        _ = FloatParameter(name="test_float", default=42)
