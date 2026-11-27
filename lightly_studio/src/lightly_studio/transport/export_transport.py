"""Transport protocol for exporting samples and annotations."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from lightly_studio.models.export_task import ExportTask
from lightly_studio.models.query_expr import QueryExpr


# TODO(Iunir, 11/2026): Send the order and the slice of the query.
class ExportTransport(Protocol):
    """Exports samples and their annotations to files."""

    def export(self, collection_id: UUID, query_expr: QueryExpr | None, task: ExportTask) -> None:
        """Export samples to a file or folder on the local machine.

        Args:
            collection_id: The ID of the collection.
            query_expr: The samples to export. None exports all samples of the collection.
                The order and the slice of a query are not sent.
            task: The export to write.
        """
