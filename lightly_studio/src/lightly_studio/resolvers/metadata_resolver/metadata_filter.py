"""Generic metadata filtering utilities."""

import operator
from typing import Any, Callable, Literal, Protocol, TypeVar

from pydantic import BaseModel
from sqlalchemy.sql.elements import ColumnElement

from lightly_studio import db_json
from lightly_studio.type_definitions import QueryType

# Type variables for generic constraints
T = TypeVar("T", bound=BaseModel)
M = TypeVar("M", bound="HasMetadata")

# Valid operators for metadata filtering
MetadataOperator = Literal[">", "<", "==", ">=", "<=", "!="]


class HasMetadata(Protocol):
    """Protocol for models that have metadata."""

    data: dict[str, Any]
    metadata_schema: dict[str, str]


class MetadataFilter(BaseModel):
    """Encapsulates a single metadata filter condition."""

    key: str
    op: MetadataOperator
    value: Any


class Metadata:
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


_OP_MAP: dict[MetadataOperator, Callable[[ColumnElement[Any], Any], ColumnElement[bool]]] = {
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

    # Apply the filters using JSON extraction
    query = query.join(
        metadata_model,
        metadata_join_condition,
    )

    for meta_filter in metadata_filters:
        extract_expr = db_json.json_extract(
            metadata_model.data,
            meta_filter.key,
            cast_to_float=isinstance(meta_filter.value, (int, float)),
        )
        compare_op = _OP_MAP[meta_filter.op]
        condition = compare_op(extract_expr, db_json.json_literal(meta_filter.value))
        query = query.where(condition)

    return query
