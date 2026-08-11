"""Generic metadata filtering utilities."""

import operator
from typing import Any, Callable, Literal, Protocol, TypeVar

import pydantic
import sqlalchemy
from pydantic import BaseModel
from pydantic_core import PydanticCustomError
from sqlalchemy.sql.elements import ColumnElement

from lightly_studio.database import db_json
from lightly_studio.type_definitions import QueryType

# Type variables for generic constraints
T = TypeVar("T", bound=BaseModel)
M = TypeVar("M", bound="HasMetadata")

# Valid operators for metadata filtering
MetadataComparisonOperator = Literal[">", "<", "==", ">=", "<=", "!="]
MetadataOperator = Literal[">", "<", "==", ">=", "<=", "!=", "in"]


class HasMetadata(Protocol):
    """Protocol for models that have metadata."""

    data: dict[str, Any]
    metadata_schema: dict[str, str]


class MetadataFilter(BaseModel):
    """Encapsulates a single metadata filter condition."""

    key: str
    op: MetadataOperator
    value: Any

    @pydantic.model_validator(mode="after")
    def validate_in_value(self) -> "MetadataFilter":  # noqa: N804
        """Validate the categorical values accepted by the ``in`` operator."""
        if self.op != "in":
            return self
        if not isinstance(self.value, list) or not self.value:
            raise PydanticCustomError(
                "metadata_in_value", "'in' metadata filters require a non-empty array."
            )
        concrete_types = {type(value) for value in self.value if value is not None}
        if not concrete_types.issubset({str, bool}) or len(concrete_types) > 1:
            raise PydanticCustomError(
                "metadata_in_value",
                "'in' metadata filter values must be homogeneous strings or booleans, "
                "optionally including null.",
            )
        return self


# Ignore PLW1641 because `==` and `!=` create filters here, so this class does
# not need normal hash behavior.
class Metadata:  # noqa: PLW1641
    """Helper class for creating metadata filters with operator syntax."""

    def __init__(self, key: str) -> None:
        """Initialize metadata filter with key."""
        self.key = key

    def __gt__(self, value: Any) -> MetadataFilter:
        """Create greater than filter."""
        return MetadataFilter(key=self.key, op=">", value=value)

    def __lt__(self, value: Any) -> MetadataFilter:
        """Create less than filter."""
        return MetadataFilter(key=self.key, op="<", value=value)

    def __ge__(self, value: Any) -> MetadataFilter:
        """Create greater than or equal filter."""
        return MetadataFilter(key=self.key, op=">=", value=value)

    def __le__(self, value: Any) -> MetadataFilter:
        """Create less than or equal filter."""
        return MetadataFilter(key=self.key, op="<=", value=value)

    def __eq__(self, value: Any) -> MetadataFilter:  # type: ignore
        """Create equality filter."""
        return MetadataFilter(key=self.key, op="==", value=value)

    def __ne__(self, value: Any) -> MetadataFilter:  # type: ignore
        """Create not equal filter."""
        return MetadataFilter(key=self.key, op="!=", value=value)


_OP_MAP: dict[
    MetadataComparisonOperator, Callable[[ColumnElement[Any], Any], ColumnElement[bool]]
] = {
    ">": operator.gt,
    "<": operator.lt,
    "==": operator.eq,
    ">=": operator.ge,
    "<=": operator.le,
    "!=": operator.ne,
}


def apply_metadata_filters(
    query: QueryType,
    metadata_filters: list[MetadataFilter],
    *,
    metadata_model: type[M],
    metadata_join_condition: Any,
) -> QueryType:
    """Apply metadata filters to a query.

    Args:
        query: The base query to filter.
        metadata_filters: The list of metadata filters to apply.
        metadata_model: The metadata table/model class.
        metadata_join_condition: The join condition between the main table
        and metadata table.

    Returns:
        The filtered query.

    Raises:
        ValueError: If any field name contains invalid characters.

    Example:
        ```python
        # Simple filters (AND by default)
        query = apply_metadata_filters(
            query,
            metadata_filters=[
                Metadata("temperature") > 25,
                Metadata("location") == "city",
            ],
            metadata_model=SampleMetadataTable,
            metadata_join_condition=SampleMetadataTable.sample_id ==
                                    ImageTable.sample_id,
        )
        ```
    """
    if not metadata_filters:
        return query

    match_missing = any(
        meta_filter.op == "in" and None in meta_filter.value for meta_filter in metadata_filters
    )
    query = query.join(
        metadata_model,
        metadata_join_condition,
        isouter=match_missing,
    )

    for meta_filter in metadata_filters:
        if meta_filter.op == "in":
            query = query.where(
                _build_in_condition(metadata_model=metadata_model, metadata_filter=meta_filter)
            )
            continue
        # Compare as text unless the value is numeric, so that the operand types match
        # on both databases; the raw JSON expression compares against neither.
        extract = (
            db_json.json_extract_as_float
            if isinstance(meta_filter.value, (int, float))
            else db_json.json_extract_as_text
        )
        extract_expr = extract(column=metadata_model.data, field=meta_filter.key)
        compare_op = _OP_MAP[meta_filter.op]
        condition = compare_op(extract_expr, meta_filter.value)
        query = query.where(condition)

    return query


def _build_in_condition(
    metadata_model: type[M], metadata_filter: MetadataFilter
) -> ColumnElement[bool]:
    """Build an OR predicate for a validated categorical ``in`` filter."""
    extract_expr = db_json.json_extract_string(
        column=metadata_model.data, field=metadata_filter.key
    )
    values = [
        str(value).lower() if isinstance(value, bool) else value
        for value in metadata_filter.value
        if value is not None
    ]
    conditions: list[ColumnElement[bool]] = []
    if values:
        conditions.append(extract_expr.in_(values))
    if None in metadata_filter.value:
        conditions.append(extract_expr.is_(None))
    return sqlalchemy.or_(*conditions)
