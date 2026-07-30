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

    The value is a list of rows, where each row maps every column name to a cell of that column's
    type. Use it when an operator needs a variable number of homogeneous multi-field inputs, for
    example segmentation prompts paired with the annotation label to assign to the resulting masks
    and the confidence threshold to apply:

    ```python
    TableParameter(
        name="prompts",
        description="Prompt to segment with and the label to assign to the masks.",
        columns=[
            StringParameter(name="prompt", description="What to segment."),
            StringParameter(name="label", default="pedestrian", required=False),
            FloatParameter(name="threshold", default=0.5, required=False),
        ],
    )
    ```

    A column is any built-in parameter, so it carries its own type, description, default and
    required flag. The GUI renders one editable column per entry using the editor for the column
    type, pre-fills new cells with the column default and lets the user add and remove rows. Tables
    cannot be nested because the GUI cannot render a table inside a cell.

    Attributes:
        columns: The columns every row must provide. At least one column is required.
    """

    columns: Sequence[BuiltinParameter[Any]] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Set up type information, check the columns and validate the default value.

        Raises:
            TypeError: If a column is not a `BuiltinParameter`.
            ValueError: If ``columns`` is empty or contains duplicate names.
        """
        self.param_type = "table"
        self.columns = _validated_columns(name=self.name, columns=self.columns)
        super().__post_init__()

    def _validate(self, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            raise TypeError(f"Expected value of type 'list' but got {type(value)}")
        columns = _validated_columns(name=self.name, columns=self.columns)
        return [
            self._validated_row(row=row, index=index, columns=columns)
            for index, row in enumerate(value)
        ]

    def _validated_row(
        self, row: Any, index: int, columns: Sequence[BuiltinParameter[Any]]
    ) -> dict[str, Any]:
        """Check a single row of the table value, validating each cell against its column.

        Args:
            row: The row to check.
            index: Position of the row in the value, used in error messages.
            columns: The columns the row must provide.

        Returns:
            The row with its cells ordered like `columns`.

        Raises:
            TypeError: If `row` is not a dict or a cell does not have the type of its column.
            ValueError: If the keys of `row` do not match the column names exactly.
        """
        if not isinstance(row, dict):
            raise TypeError(f"Expected row {index} of type 'dict' but got {type(row)}")
        column_names = [column.name for column in columns]
        if set(row) != set(column_names):
            raise ValueError(
                f"Row {index} must have exactly the columns {column_names} but got {sorted(row)}"
            )
        validated_row = {}
        for column in columns:
            try:
                validated_row[column.name] = column._validate(row[column.name])  # noqa: SLF001
            except TypeError as ex:
                raise TypeError(f"Invalid cell '{column.name}' in row {index}: {ex}") from ex
        return validated_row


def _validated_columns(
    name: str, columns: Sequence[BuiltinParameter[Any]]
) -> list[BuiltinParameter[Any]]:
    """Check the columns of a table parameter.

    Args:
        name: Name of the parameter, used in error messages.
        columns: The columns to check.

    Returns:
        The columns as a list.

    Raises:
        TypeError: If a column is not a `BuiltinParameter`.
        ValueError: If `columns` is empty or contains duplicate names.
    """
    if not columns:
        raise ValueError(f"Table parameter '{name}' must define at least one column")
    for column in columns:
        if not isinstance(column, BuiltinParameter):
            raise TypeError(f"Expected column of type 'BuiltinParameter' but got {type(column)}")
    column_names = [column.name for column in columns]
    if len(set(column_names)) != len(column_names):
        raise ValueError(
            f"Columns of table parameter '{name}' must be unique but got {column_names}"
        )
    return list(columns)
