"""Metadata models for storing custom metadata."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.types import JSON
from sqlmodel import Field, Relationship, SQLModel

from lightly_studio.metadata.complex_metadata import (
    COMPLEX_METADATA_TYPES,
    deserialize_complex_metadata,
    serialize_complex_metadata,
)
from lightly_studio.models.sample import SampleTable

TYPE_TO_NAME_MAP = {
    bool: "boolean",
    int: "integer",
    float: "float",
    str: "string",
    list: "list",
    dict: "dict",
}

NAME_TO_TYPE_MAP = {
    "string": str,
    "integer": int,
    "float": float,
    "boolean": bool,
    "list": list,
    "dict": dict,
}


def get_type_name(value: Any) -> str:
    """Get the type name for a value.

    Args:
        value: The value to get the type name for.

    Returns:
        The type name as a string.
    """
    if value is None:
        return "null"
    # Check if it's a complex metadata type.
    for name, cls in COMPLEX_METADATA_TYPES.items():
        if isinstance(value, cls):
            return name

    # Return mapped type name or fallback to class name.
    return TYPE_TO_NAME_MAP.get(type(value), type(value).__name__.lower())


def validate_type_compatibility(expected_type: str, value: Any) -> bool:
    """Validate that a value is compatible with an expected type.

    Args:
        expected_type: The expected type name.
        value: The value to validate.

    Returns:
        True if compatible, False otherwise.
    """
    if value is None:
        return expected_type == "null"

    # Check complex types.
    if expected_type in COMPLEX_METADATA_TYPES:
        expected_complex_cls = COMPLEX_METADATA_TYPES[expected_type]
        assert expected_complex_cls is not None
        return isinstance(value, expected_complex_cls)

    # Check simple types
    expected_cls = NAME_TO_TYPE_MAP.get(expected_type)
    if expected_cls is None:
        return False

    return isinstance(value, expected_cls)


class MetadataBase(SQLModel):
    """Base class for CustomMetadata models."""

    custom_metadata_id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    # Dictionary storing the actual metadata values as JSON.
    data: dict[str, Any] = Field(
        default_factory=dict,
        sa_type=JSON,
        description="Custom metadata stored as JSON",
    )
    # Dictionary storing the metadata schema.
    metadata_schema: dict[str, str] = Field(
        default_factory=dict,
        sa_type=JSON,
        description="Schema information for metadata keys",
    )

    def ensure_schema(self, key: str, value: Any) -> None:
        """Ensure schema exists for a key and validate value type.

        This method handles schema management for metadata keys:
         If the key doesn't exist in the schema, it creates a new entry
         with the inferred type from the provided value
         If the key exists, it validates that the new value matches
         the expected type from the schema

        This ensures type consistency across metadata operations and prevents
        accidental type mismatches that could cause issues in applications.

        Args:
            key: The metadata key to validate/update schema for
            value: The value to validate/use for type inference

        Raises:
            ValueError: If the value type doesn't match existing schema
        """
        if key not in self.metadata_schema:
            # New key - create schema with actual type name.
            self.metadata_schema[key] = get_type_name(value)
        else:
            # Existing key - validate type.
            existing_type = self.metadata_schema[key]
            if not validate_type_compatibility(existing_type, value):
                raise ValueError(
                    f"Value type mismatch for key '{key}'. "
                    f"Expected {existing_type}, got {get_type_name(value)}."
                )

    def set_value(self, key: str, value: Any) -> None:
        """Set a metadata value with schema validation and database tracking.

        Args:
            key: The metadata key to set
            value: The value to set

        Raises:
            ValueError: If the value type doesn't match the schema
        """
        self.ensure_schema(key, value)
        # Serialize complex metadata for storage.
        self.data[key] = serialize_complex_metadata(value)
        self.updated_at = datetime.now(timezone.utc)
        # Mark the object as modified so SQLAlchemy knows to update it.
        flag_modified(self, "data")
        flag_modified(self, "metadata_schema")

    def get_value(self, key: str) -> Any:
        """Get a metadata value with automatic deserialization.

        Args:
            key: The metadata key.

        Returns:
            The deserialized value (complex metadata object if applicable)
            or None if the key doesn't exist.
        """
        value = self.data.get(key)
        if value is not None:
            # Get expected type from schema for deserialization.
            expected_type = self.metadata_schema.get(key)
            if expected_type:
                return deserialize_complex_metadata(value, expected_type)
        return value


class MetadataCreate(MetadataBase):
    """Input class for Metadata model."""


class SampleMetadataTable(MetadataBase, table=True):
    """This class defines the SampleMetadataTable model."""

    __tablename__ = "metadata"
    sample_id: UUID = Field(foreign_key="sample.sample_id", unique=True)

    sample: SampleTable = Relationship(back_populates="metadata_dict")


class SampleMetadataView(SQLModel):
    """Sample metadata class when retrieving."""

    data: dict[str, Any]


class MetadataInfoView(BaseModel):
    """Metadata info response model for API endpoints."""

    name: str = Field(description="The metadata key name")
    type: str = Field(description="The metadata type (e.g., 'string', 'integer', 'float')")
    min: int | float | None = Field(None, description="Minimum value for numerical metadata")
    max: int | float | None = Field(None, description="Maximum value for numerical metadata")
