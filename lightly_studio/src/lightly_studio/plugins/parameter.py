"""Parameter for operators for LightlyStudio plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass
class BaseParameter(ABC):
    """Base parameter definition shared across operator parameters."""

    name: str
    description: str = ""
    default: Any = None
    required: bool = True
    param_type: str | None = None

    def __post_init__(self) -> None:
        """Run value validation once the dataclass is initialized."""
        if self.default is not None:
            self.default = self._validate(self.default)

    @abstractmethod
    def _validate(self, value: Any) -> Any:
        """Validate the parameter value."""


class BuiltinParameter(BaseParameter, Generic[T]):
    """Represents a built-in operator parameter."""

    def __post_init__(self) -> None:
        """Set up type information and validate default value.

        Raises:
            NotImplementedError: If the subclass does not define ``_parameter_type``.
        """
        if not hasattr(self, "_parameter_type") or self._parameter_type is None:
            raise NotImplementedError("Subclasses must define _parameter_type class attribute")
        self._type = self._parameter_type
        self.param_type = self._parameter_type.__name__
        super().__post_init__()

    def _validate(self, value: T) -> T:
        if isinstance(value, self._type):
            return value
        raise TypeError(f"Expected value of type '{self._type.__name__}' but got {type(value)}'")


class IntParameter(BuiltinParameter[int]):
    """Represents an integer operator parameter."""

    _parameter_type = int


class FloatParameter(BuiltinParameter[float]):
    """Represents a float operator parameter."""

    _parameter_type = float


class BoolParameter(BuiltinParameter[bool]):
    """Represents a boolean operator parameter."""

    _parameter_type = bool


class StringParameter(BuiltinParameter[str]):
    """Represents a string operator parameter."""

    _parameter_type = str


@dataclass
class TableParameter(BaseParameter):
    """Represents a tabular operator parameter.

    The value is a list of rows, where each row maps every column name to a string cell. Use it
    when an operator needs a variable number of homogeneous multi-field inputs, for example
    segmentation prompts paired with the annotation label to assign to the resulting masks:

    ```python
    TableParameter(
        name="prompts",
        description="Prompt to segment with and the label to assign to the masks.",
        columns=[
            StringParameter(name="prompt", description="What to segment."),
            StringParameter(name="label", default="pedestrian", required=False),
        ],
    )
    ```

    Every column is a `StringParameter`, so a column ships its own description, default and
    required flag. The GUI renders one editable text column per entry, pre-fills new cells with the
    column default and lets the user add and remove rows.

    Attributes:
        columns: The columns every row must provide. At least one column is required.
    """

    columns: Sequence[StringParameter] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Set up type information, check the columns and validate the default value.

        Raises:
            TypeError: If a column is not a `StringParameter`.
            ValueError: If ``columns`` is empty or contains duplicate names.
        """
        self.param_type = "table"
        self.columns = _validated_columns(name=self.name, columns=self.columns)
        super().__post_init__()

    def _validate(self, value: Any) -> list[dict[str, str]]:
        if not isinstance(value, list):
            raise TypeError(f"Expected value of type 'list' but got {type(value)}")
        columns = _validated_columns(name=self.name, columns=self.columns)
        return [
            _validated_row(row=row, index=index, columns=columns) for index, row in enumerate(value)
        ]


def _validated_columns(name: str, columns: Sequence[StringParameter]) -> list[StringParameter]:
    """Check the columns of a table parameter.

    Args:
        name: Name of the parameter, used in error messages.
        columns: The columns to check.

    Returns:
        The columns as a list.

    Raises:
        TypeError: If a column is not a `StringParameter`.
        ValueError: If `columns` is empty or contains duplicate names.
    """
    if not columns:
        raise ValueError(f"Table parameter '{name}' must define at least one column")
    for column in columns:
        if not isinstance(column, StringParameter):
            raise TypeError(f"Expected column of type 'StringParameter' but got {type(column)}")
    column_names = [column.name for column in columns]
    if len(set(column_names)) != len(column_names):
        raise ValueError(
            f"Columns of table parameter '{name}' must be unique but got {column_names}"
        )
    return list(columns)


def _validated_row(row: Any, index: int, columns: Sequence[StringParameter]) -> dict[str, str]:
    """Check a single row of a table parameter value.

    Args:
        row: The row to check.
        index: Position of the row in the value, used in error messages.
        columns: The columns the row must provide.

    Returns:
        The row with its cells ordered like `columns`.

    Raises:
        TypeError: If `row` is not a dict or a cell is not a string.
        ValueError: If the keys of `row` do not match the column names exactly.
    """
    if not isinstance(row, dict):
        raise TypeError(f"Expected row {index} of type 'dict' but got {type(row)}")
    column_names = [column.name for column in columns]
    if set(row) != set(column_names):
        raise ValueError(
            f"Row {index} must have exactly the columns {column_names} but got {sorted(row)}"
        )
    for column_name in column_names:
        if not isinstance(row[column_name], str):
            raise TypeError(
                f"Expected cell '{column_name}' in row {index} of type 'str' "
                f"but got {type(row[column_name])}"
            )
    return {column_name: row[column_name] for column_name in column_names}
