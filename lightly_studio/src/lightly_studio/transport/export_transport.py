"""Transport protocol for exporting samples and annotations."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from lightly_studio.models.export_task import ExportTask
from lightly_studio.models.sample_query import SampleQueryRequest


class ExportTransport(Protocol):
    """Exports samples and their annotations to files."""

    def export(
        self, collection_id: UUID, request: SampleQueryRequest, limit: int | None, task: ExportTask
    ) -> None:
        """Export samples to a file or folder on the local machine.

        Args:
            collection_id: The ID of the collection.
            request: The filter, the sort and the offset of the samples to export. The
                `cursor` and the `limit` of the request are not used.
            limit: The maximum number of samples to export. None exports all.
            task: The export to write.
        """
