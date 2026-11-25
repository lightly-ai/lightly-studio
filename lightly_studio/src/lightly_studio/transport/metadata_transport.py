"""Transport protocol for sample metadata."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol
from uuid import UUID


class MetadataTransport(Protocol):
    """Gets and changes the metadata of samples."""

    def get(self, sample_ids: Sequence[UUID]) -> dict[UUID, dict[str, Any]]:
        """Get the metadata of samples.

        Values of a complex type, for example `GPSCoordinate`, are objects of that type.

        Returns:
            The metadata for each sample ID. A sample without metadata is not in the result.
        """

    def update(self, sample_metadata: Sequence[tuple[UUID, Mapping[str, Any]]]) -> None:
        """Merge new metadata into the metadata of samples.

        Args:
            sample_metadata: Pairs of a sample ID and the metadata to merge, for example
                `{"weather": "cloudy"}`. Keys that are already set get the new value.

        Raises:
            ValueError: If the type of a value is not the type that the key has.
        """
