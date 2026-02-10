"""Generic metadata filtering utilities."""

import json
import re
from typing import Any, Dict, List, Literal, Protocol, Type, TypeVar

from pydantic import BaseModel
from sqlalchemy import text

from lightly_studio import db_manager
from lightly_studio.db_manager import DatabaseBackend
from lightly_studio.resolvers.metadata_resolver.json_utils import (
    json_extract_sql,
)
from lightly_studio.type_definitions import QueryType

# Type variables for generic constraints
T = TypeVar("T", bound=BaseModel)
M = TypeVar("M", bound="HasMetadata")

# Valid operators for metadata filtering
MetadataOperator = Literal[">", "<", "==", ">=", "<=", "!="]


class HasMetadata(Protocol):
    """Protocol for models that have metadata."""

    data: Dict[str, Any]
    metadata_schema: Dict[str, str]


class MetadataFilter(BaseModel):
    """Encapsulates a single metadata filter condition."""

    key: str
    op: MetadataOperator
    value: Any

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization hook to serialize string values."""
        # Pre-serialize string values for JSON comparison
        if isinstance(self.value, str):
            # Avoid double-serialization
            try:
                json.loads(self.value)
                # Already serialized, don't serialize again
            except (json.JSONDecodeError, TypeError):
                # Not serialized, serialize it
                self.value = json.dumps(self.value)


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


def _sanitize_param_name(field: str) -> str:
    """Sanitize field name for use as SQL parameter name.

    Args:
        field: The field name (may contain dots for nested paths).

    Returns:
        A sanitized parameter name safe for SQL binding.
    """
    # Replace dots and other problematic characters with underscores
    return re.sub(r"[^a-zA-Z0-9_]", "_", field)


def apply_metadata_filters(
    query: QueryType,
    metadata_filters: List[MetadataFilter],
    *,
    metadata_model: Type[M],
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

    backend = db_manager.get_backend()

    for i, meta_filter in enumerate(metadata_filters):
        field = meta_filter.key
        value = meta_filter.value
        op = meta_filter.op

        # Add unique identifier to parameter name to avoid conflicts
        param_name = f"{_sanitize_param_name(field)}_{i}"

        json_expr = json_extract_sql(field, cast_to_float=isinstance(value, (int, float)))
        condition = f"{json_expr} {op} :{param_name}"

        # PostgreSQL ->> returns raw text, but MetadataFilter pre-serializes
        # string values with json.dumps() for DuckDB's json_extract().
        # Unwrap the JSON encoding for Postgres.
        if backend == DatabaseBackend.POSTGRESQL and isinstance(value, str):
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                pass

        query = query.where(text(condition).bindparams(**{param_name: value}))

    return query
