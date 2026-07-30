import re
from dataclasses import asdict

import pytest

from lightly_studio.plugins.parameter import (
    BoolParameter,
    FloatParameter,
    IntParameter,
    StringParameter,
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


class TestTableParameter:
    def test_init(self) -> None:
        param = TableParameter(
            name="prompts",
            description="abc",
            columns=[StringParameter(name="prompt"), StringParameter(name="label")],
            default=[{"prompt": "person", "label": "pedestrian"}],
            required=False,
        )

        assert asdict(param) == {
            "name": "prompts",
            "description": "abc",
            "default": [{"prompt": "person", "label": "pedestrian"}],
            "required": False,
            "param_type": "table",
            "columns": [
                {
                    "name": "prompt",
                    "description": "",
                    "default": None,
                    "required": True,
                    "param_type": "str",
                },
                {
                    "name": "label",
                    "description": "",
                    "default": None,
                    "required": True,
                    "param_type": "str",
                },
            ],
        }

    def test_init__no_default(self) -> None:
        param = TableParameter(
            name="prompts",
            columns=[StringParameter(name="prompt"), StringParameter(name="label")],
        )

        assert param.default is None
        assert [column.name for column in param.columns] == ["prompt", "label"]

    def test_init__column_default_and_required(self) -> None:
        # A column carries its own default and required flag, which the GUI uses to pre-fill new
        # cells and to decide which cells must be filled in.
        param = TableParameter(
            name="prompts",
            columns=[
                StringParameter(name="prompt"),
                StringParameter(name="label", default="pedestrian", required=False),
            ],
        )

        assert param.columns[0].default is None
        assert param.columns[0].required
        assert param.columns[1].default == "pedestrian"
        assert not param.columns[1].required

    def test_init__empty_default(self) -> None:
        # An empty table is a valid default and must not be confused with "no default".
        param = TableParameter(name="prompts", columns=[StringParameter(name="prompt")], default=[])

        assert param.default == []

    def test_init__default_cells_ordered_like_columns(self) -> None:
        param = TableParameter(
            name="prompts",
            columns=[StringParameter(name="prompt"), StringParameter(name="label")],
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
            _ = TableParameter(
                name="prompts",
                columns=[StringParameter(name="prompt"), StringParameter(name="prompt")],
            )

    def test_init__column_not_a_parameter(self) -> None:
        with pytest.raises(
            TypeError,
            match=re.escape("Expected column of type 'BuiltinParameter' but got <class 'str'>"),
        ):
            _ = TableParameter(name="prompts", columns=["prompt"])  # type: ignore[list-item]

    def test_init__nested_table_column(self) -> None:
        # A table inside a table is not supported by the GUI, so it must fail loudly instead of
        # being rendered as an empty column.
        nested = TableParameter(name="nested", columns=[StringParameter(name="prompt")])

        with pytest.raises(
            TypeError,
            match=re.escape(
                "Expected column of type 'BuiltinParameter' but got "
                "<class 'lightly_studio.plugins.parameter.TableParameter'>"
            ),
        ):
            _ = TableParameter(name="prompts", columns=[nested])  # type: ignore[list-item]

    def test_init__default_not_a_list(self) -> None:
        with pytest.raises(
            TypeError, match=re.escape("Expected value of type 'list' but got <class 'dict'>")
        ):
            _ = TableParameter(
                name="prompts",
                columns=[StringParameter(name="prompt")],
                default={"prompt": "person"},
            )

    def test_init__row_not_a_dict(self) -> None:
        with pytest.raises(
            TypeError, match=re.escape("Expected row 0 of type 'dict' but got <class 'str'>")
        ):
            _ = TableParameter(
                name="prompts", columns=[StringParameter(name="prompt")], default=["person"]
            )

    def test_init__missing_column(self) -> None:
        with pytest.raises(
            ValueError,
            match=re.escape(
                "Row 0 must have exactly the columns ['prompt', 'label'] but got ['prompt']"
            ),
        ):
            _ = TableParameter(
                name="prompts",
                columns=[StringParameter(name="prompt"), StringParameter(name="label")],
                default=[{"prompt": "person"}],
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
                columns=[StringParameter(name="prompt")],
                default=[{"prompt": "person", "confidence": "0.5"}],
            )

    def test_init__mixed_column_types(self) -> None:
        param = TableParameter(
            name="prompts",
            columns=[
                StringParameter(name="prompt"),
                FloatParameter(name="threshold"),
                IntParameter(name="max_masks"),
                BoolParameter(name="enabled"),
            ],
            default=[{"prompt": "person", "threshold": 0.5, "max_masks": 3, "enabled": True}],
        )

        assert param.default == [
            {"prompt": "person", "threshold": 0.5, "max_masks": 3, "enabled": True}
        ]

    def test_init__cell_type_does_not_match_column(self) -> None:
        with pytest.raises(
            TypeError,
            match=re.escape(
                "Invalid cell 'threshold' in row 0: Expected value of type 'float' but got "
                "<class 'str'>"
            ),
        ):
            _ = TableParameter(
                name="prompts",
                columns=[FloatParameter(name="threshold")],
                default=[{"threshold": "0.5"}],
            )

    def test_init__reports_second_row_index(self) -> None:
        # The row index in the message must point at the offending row, not always row 0.
        with pytest.raises(ValueError, match="Row 1 must have exactly"):
            _ = TableParameter(
                name="prompts",
                columns=[StringParameter(name="prompt")],
                default=[{"prompt": "person"}, {}],
            )
