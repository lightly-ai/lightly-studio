import re
from dataclasses import asdict

import pytest

from lightly_studio.plugins.parameter import (
    FloatParameter,
    IntParameter,
    TableParameter,
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
        "columns": None,
    }


def test_builtin_parameters() -> None:
    # Test some variants as representative for all built-in parameters
    _ = IntParameter(name="test_int")
    _ = IntParameter(name="test_int", default=42)
    _ = IntParameter(name="test_int", default=True)
    _ = FloatParameter(name="test_float", default=42.0)

    # invalid default types
    with pytest.raises(TypeError, match="Expected value of type 'int' but got <class 'str'>"):
        _ = IntParameter(name="test_int", default="42")
    with pytest.raises(TypeError, match="Expected value of type 'int' but got <class 'float'>"):
        _ = IntParameter(name="test_int", default=42.0)
    with pytest.raises(TypeError, match="Expected value of type 'float' but got <class 'int'>"):
        _ = FloatParameter(name="test_float", default=42)


def test_builtin_parameters__columns_rejected() -> None:
    # Columns are inherited from BaseParameter but only meaningful for TableParameter, so setting
    # them on a scalar parameter must fail loudly instead of being silently ignored.
    with pytest.raises(ValueError, match="Parameter 'test_int' of type 'int' has no columns"):
        _ = IntParameter(name="test_int", columns=["a"])


class TestTableParameter:
    def test_init(self) -> None:
        param = TableParameter(
            name="prompts",
            description="abc",
            columns=["prompt", "label"],
            default=[{"prompt": "person", "label": "pedestrian"}],
            required=False,
        )

        assert asdict(param) == {
            "name": "prompts",
            "description": "abc",
            "default": [{"prompt": "person", "label": "pedestrian"}],
            "required": False,
            "param_type": "table",
            "columns": ["prompt", "label"],
        }

    def test_init__no_default(self) -> None:
        param = TableParameter(name="prompts", columns=["prompt", "label"])

        assert param.default is None
        assert param.columns == ["prompt", "label"]

    def test_init__empty_default(self) -> None:
        # An empty table is a valid default and must not be confused with "no default".
        param = TableParameter(name="prompts", columns=["prompt"], default=[])

        assert param.default == []

    def test_init__default_cells_ordered_like_columns(self) -> None:
        param = TableParameter(
            name="prompts",
            columns=["prompt", "label"],
            default=[{"label": "pedestrian", "prompt": "person"}],
        )

        assert list(param.default[0]) == ["prompt", "label"]

    def test_init__missing_columns(self) -> None:
        with pytest.raises(
            ValueError, match="Table parameter 'prompts' must define at least one column"
        ):
            _ = TableParameter(name="prompts")

    def test_init__empty_columns(self) -> None:
        with pytest.raises(
            ValueError, match="Table parameter 'prompts' must define at least one column"
        ):
            _ = TableParameter(name="prompts", columns=[])

    def test_init__duplicate_columns(self) -> None:
        with pytest.raises(
            ValueError,
            match=re.escape(
                "Columns of table parameter 'prompts' must be unique but got ['prompt', 'prompt']"
            ),
        ):
            _ = TableParameter(name="prompts", columns=["prompt", "prompt"])

    def test_init__non_string_column(self) -> None:
        with pytest.raises(
            TypeError,
            match=re.escape("Expected column name of type 'str' but got <class 'int'>"),
        ):
            _ = TableParameter(name="prompts", columns=["prompt", 1])  # type: ignore[list-item]

    def test_init__default_not_a_list(self) -> None:
        with pytest.raises(
            TypeError, match=re.escape("Expected value of type 'list' but got <class 'dict'>")
        ):
            _ = TableParameter(name="prompts", columns=["prompt"], default={"prompt": "person"})

    def test_init__row_not_a_dict(self) -> None:
        with pytest.raises(
            TypeError, match=re.escape("Expected row 0 of type 'dict' but got <class 'str'>")
        ):
            _ = TableParameter(name="prompts", columns=["prompt"], default=["person"])

    def test_init__missing_column(self) -> None:
        with pytest.raises(
            ValueError,
            match=re.escape(
                "Row 0 must have exactly the columns ['prompt', 'label'] but got ['prompt']"
            ),
        ):
            _ = TableParameter(
                name="prompts", columns=["prompt", "label"], default=[{"prompt": "person"}]
            )

    def test_init__extra_column(self) -> None:
        with pytest.raises(
            ValueError,
            match=re.escape(
                "Row 0 must have exactly the columns ['prompt'] but got ['confidence', 'prompt']"
            ),
        ):
            _ = TableParameter(
                name="prompts",
                columns=["prompt"],
                default=[{"prompt": "person", "confidence": "0.5"}],
            )

    def test_init__cell_not_a_string(self) -> None:
        with pytest.raises(
            TypeError,
            match=re.escape("Expected cell 'prompt' in row 0 of type 'str' but got <class 'int'>"),
        ):
            _ = TableParameter(name="prompts", columns=["prompt"], default=[{"prompt": 1}])

    def test_init__reports_second_row_index(self) -> None:
        # The row index in the message must point at the offending row, not always row 0.
        with pytest.raises(ValueError, match="Row 1 must have exactly"):
            _ = TableParameter(
                name="prompts", columns=["prompt"], default=[{"prompt": "person"}, {}]
            )
