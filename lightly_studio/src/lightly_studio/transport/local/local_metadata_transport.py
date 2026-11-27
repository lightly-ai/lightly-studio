"""Metadata transport that calls the resolvers in the same process."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from lightly_studio.database import db_manager
from lightly_studio.resolvers import metadata_resolver


class LocalMetadataTransport:
    """Implements `MetadataTransport` with the persistent database session."""

    def get(self, sample_ids: Sequence[UUID]) -> dict[UUID, dict[str, Any]]:
        """Get the metadata of samples. A sample without metadata is not in the result."""
        rows = metadata_resolver.get_by_sample_ids(
            session=db_manager.persistent_session(), sample_ids=sample_ids
        )
        return {row.sample_id: {key: row.get_value(key=key) for key in row.data} for row in rows}

    def update(self, sample_metadata: Sequence[tuple[UUID, Mapping[str, Any]]]) -> None:
        """Merge new metadata into the metadata of samples."""
        metadata_resolver.bulk_update_metadata(
            session=db_manager.persistent_session(), sample_metadata=list(sample_metadata)
        )
