"""Parameter for operators for LightlyStudio plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
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
    columns: list[str] | None = None

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
            ValueError: If ``columns`` is set, as it is only meaningful for table parameters.
        """
        if not hasattr(self, "_parameter_type") or self._parameter_type is None:
            raise NotImplementedError("Subclasses must define _parameter_type class attribute")
        self._type = self._parameter_type
        self.param_type = self._parameter_type.__name__
        # Columns are inherited from BaseParameter but only apply to TableParameter. Rejecting them
        # here surfaces the mistake instead of silently dropping them.
        if self.columns is not None:
            raise ValueError(
                f"Parameter '{self.name}' of type '{self.param_type}' has no columns, "
                f"but got {list(self.columns)}"
            )
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


class TableParameter(BaseParameter):
    """Represents a tabular operator parameter.

    The value is a list of rows, where each row maps every column name to a string cell. Use it
    when an operator needs a variable number of homogeneous multi-field inputs, for example
    segmentation prompts paired with the annotation label to assign to the resulting masks:

    ```python
    TableParameter(
        name="prompts",
        description="Prompt to segment with and the label to assign to the masks.",
        columns=["prompt", "label"],
        default=[{"prompt": "person", "label": "pedestrian"}],
    )
    ```

    `columns` is inherited from `BaseParameter` and is required here. The GUI renders one editable
    text column per entry and lets the user add and remove rows.
    """

    def __post_init__(self) -> None:
        """Set up type information, check the columns and validate the default value.

        Raises:
            TypeError: If a column name is not a string.
            ValueError: If ``columns`` is empty or contains duplicates.
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


def _validated_columns(name: str, columns: Sequence[str] | None) -> list[str]:
    """Check the column names of a table parameter.

    Args:
        name: Name of the parameter, used in error messages.
        columns: The column names to check.

    Returns:
        The column names as a list.

    Raises:
        TypeError: If a column name is not a string.
        ValueError: If `columns` is empty or contains duplicates.
    """
    if not columns:
        raise ValueError(f"Table parameter '{name}' must define at least one column")
    for column in columns:
        if not isinstance(column, str):
            raise TypeError(f"Expected column name of type 'str' but got {type(column)}")
    if len(set(columns)) != len(columns):
        raise ValueError(
            f"Columns of table parameter '{name}' must be unique but got {list(columns)}"
        )
    return list(columns)


def _validated_row(row: Any, index: int, columns: Sequence[str]) -> dict[str, str]:
    """Check a single row of a table parameter value.

    Args:
        row: The row to check.
        index: Position of the row in the value, used in error messages.
        columns: The column names the row must provide.

    Returns:
        The row with its cells ordered like `columns`.

    Raises:
        TypeError: If `row` is not a dict or a cell is not a string.
        ValueError: If the keys of `row` do not match `columns` exactly.
    """
    if not isinstance(row, dict):
        raise TypeError(f"Expected row {index} of type 'dict' but got {type(row)}")
    if set(row) != set(columns):
        raise ValueError(
            f"Row {index} must have exactly the columns {list(columns)} but got {sorted(row)}"
        )
    for column in columns:
        if not isinstance(row[column], str):
            raise TypeError(
                f"Expected cell '{column}' in row {index} of type 'str' but got {type(row[column])}"
            )
    return {column: row[column] for column in columns}
