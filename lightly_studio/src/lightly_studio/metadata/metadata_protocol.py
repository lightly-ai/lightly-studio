"""Protocol for complex metadata types that can be stored in JSON columns."""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ComplexMetadata(Protocol):
    """Protocol for complex types that can be serialized to/from JSON."""

    def as_dict(self) -> dict[str, Any]:
        """Convert the complex metadata to a dictionary for JSON storage."""
        ...

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ComplexMetadata":
        """Create the complex metadata from a dictionary."""
        ...
