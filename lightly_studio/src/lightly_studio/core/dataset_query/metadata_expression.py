"""Metadata field access and comparisons for dataset queries."""

from __future__ import annotations

import operator
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, Union

from sqlalchemy import ColumnElement, Double, and_, case, exists
from sqlmodel import col, select

from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.database import db_json
from lightly_studio.models.metadata import SampleMetadataTable
from lightly_studio.models.sample import SampleTable

MetadataValue = Union[str, bool, int, float]
MetadataComparison = Literal["==", "!=", "<", "<=", ">", ">="]


class MetadataAccessor:
    """Access metadata fields by dot-separated paths and array indices.

    Example:
        ``ImageSampleField.metadata["odometry.camera"] == "front"``
    """

    def __getitem__(self, path: str) -> MetadataField:
        """Return a metadata field for the given path.

        Args:
            path: Dot-separated metadata path, with optional array indices.

        Returns:
            A field reference for the requested metadata path.
        """
        return MetadataField(path=path)


class MetadataField:  # noqa: PLW1641
    """Compare metadata using the type of the comparison value.

    Strings, booleans, and numbers compare as their JSON types. Integers and
    floats compare numerically. Ordering requires a numeric comparison value.
    Values of another type, missing paths, and JSON null do not match,
    including inequality.

    Attributes:
        path: Dot-separated metadata path, with optional array indices.
    """

    def __init__(self, path: str) -> None:
        """Initialize a metadata field reference."""
        self.path = path

    def __eq__(self, other: MetadataValue) -> MatchExpression:  # type: ignore[override]
        """Create an equality filter."""
        return self._expression(other=other, comparison="==")

    def __ne__(self, other: MetadataValue) -> MatchExpression:  # type: ignore[override]
        """Create an inequality filter."""
        return self._expression(other=other, comparison="!=")

    def __lt__(self, other: int | float) -> MatchExpression:
        """Create a numeric less-than filter."""
        return self._expression(other=other, comparison="<")

    def __le__(self, other: int | float) -> MatchExpression:
        """Create a numeric less-than-or-equal filter."""
        return self._expression(other=other, comparison="<=")

    def __gt__(self, other: int | float) -> MatchExpression:
        """Create a numeric greater-than filter."""
        return self._expression(other=other, comparison=">")

    def __ge__(self, other: int | float) -> MatchExpression:
        """Create a numeric greater-than-or-equal filter."""
        return self._expression(other=other, comparison=">=")

    def _expression(self, other: MetadataValue, comparison: MetadataComparison) -> MatchExpression:
        if not isinstance(other, (str, bool, int, float)):
            raise TypeError("Metadata comparisons require a string, boolean, or number.")
        # bool subclasses int, so numeric ordering must explicitly reject booleans.
        if comparison not in ("==", "!=") and (
            isinstance(other, bool) or not isinstance(other, (int, float))
        ):
            raise TypeError("Metadata ordering comparisons require a number.")
        return MetadataComparisonExpression(path=self.path, comparison=comparison, value=other)


@dataclass
class MetadataComparisonExpression(MatchExpression):
    """Match a sample's metadata with a correlated EXISTS condition.

    Attributes:
        path: Dot-separated metadata path, with optional array indices.
        comparison: Equality, inequality, or numeric ordering operator.
        value: String, boolean, or number to compare with the stored JSON value.
    """

    path: str
    comparison: MetadataComparison
    value: MetadataValue

    def get(self) -> ColumnElement[bool]:
        """Build a predicate without adding a join to the outer query."""
        condition = self._condition()
        return exists(
            select(1)
            .select_from(SampleMetadataTable)
            .where(col(SampleMetadataTable.sample_id) == col(SampleTable.sample_id))
            .where(condition)
            .correlate(SampleTable)
        )

    def _condition(self) -> ColumnElement[bool]:
        # metadata_schema records only top-level types; nested leaf types come from data.
        scalar_type = db_json.json_extract_scalar_type(
            column=SampleMetadataTable.data, field=self.path
        )
        operations: dict[
            MetadataComparison, Callable[[ColumnElement[Any], Any], ColumnElement[bool]]
        ] = {
            "==": operator.eq,
            "!=": operator.ne,
            "<": operator.lt,
            "<=": operator.le,
            ">": operator.gt,
            ">=": operator.ge,
        }
        if isinstance(self.value, (int, float)) and not isinstance(self.value, bool):
            # CASE guards the cast even if the database reorders WHERE predicates.
            numeric_value = case(
                (
                    scalar_type == "number",
                    db_json.json_extract_as_text(
                        column=SampleMetadataTable.data, field=self.path
                    ).cast(Double),
                ),
            )
            return operations[self.comparison](numeric_value, self.value)
        expected_type = "boolean" if isinstance(self.value, bool) else "string"
        extracted = db_json.json_extract_as_text(column=SampleMetadataTable.data, field=self.path)
        value = str(self.value).lower() if expected_type == "boolean" else self.value
        return and_(
            scalar_type == expected_type,
            operations[self.comparison](extracted, value),
        )
