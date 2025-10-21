"""Protocol for complex metadata types that can be stored in JSON columns."""

from typing import Any, Dict, Protocol, runtime_checkable


@runtime_checkable
class ComplexMetadata(Protocol):
    """Protocol for complex types that can be serialized to/from JSON."""

    def as_dict(self) -> Dict[str, Any]:
        """Convert the complex metadata to a dictionary for JSON storage."""
        ...

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComplexMetadata":
        """Create the complex metadata from a dictionary."""
        ...
