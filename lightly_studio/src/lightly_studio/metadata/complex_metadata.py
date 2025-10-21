"""Complex metadata types that can be stored in JSON columns."""

from typing import Any, Dict, Type

from lightly_studio.metadata.gps_coordinate import GPSCoordinate
from lightly_studio.metadata.metadata_protocol import ComplexMetadata

# Registry of complex metadata types for automatic serialization/deserialization
COMPLEX_METADATA_TYPES: Dict[str, Type[ComplexMetadata]] = {
    "gps_coordinate": GPSCoordinate,
}


def serialize_complex_metadata(value: Any) -> Any:
    """Serialize complex metadata for JSON storage.

    Args:
        value: Value to serialize.

    Returns:
        Serialized value if it is ComplexMetadata, the original
        value otherwise.
    """
    if isinstance(value, ComplexMetadata):
        return value.as_dict()

    return value


def deserialize_complex_metadata(value: Any, expected_type: str) -> Any:
    """Deserialize complex metadata from JSON storage.

    Args:
        value: Value to deserialize.
        expected_type: Expected type name from schema (e.g., "gps_coordinate").

    Returns:
        Deserialized value (complex metadata object if applicable).
    """
    # If we have an expected type and the value is a dict, try to deserialize.
    if expected_type and isinstance(value, dict) and expected_type in COMPLEX_METADATA_TYPES:
        try:
            return COMPLEX_METADATA_TYPES[expected_type].from_dict(value)
        except (KeyError, TypeError):
            # If deserialization fails, return the original value.
            pass
    return value
