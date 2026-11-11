"""Transport protocol for exporting samples and annotations."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol
from uuid import UUID

from lightly_studio.models.export_format import ExportFormat
from lightly_studio.models.query_expr import QueryExpr


# TODO(Iunir, 11/2026): Send the order and the slice of the query.
class ExportTransport(Protocol):
    """Exports samples and their annotations to files."""

    def export(
        self,
        collection_id: UUID,
        query_expr: QueryExpr | None,
        export_format: ExportFormat,
        output_path: Path,
        annotation_collection_id: UUID | None,
    ) -> None:
        """Export samples to a file or folder on the local machine.

        Args:
            collection_id: The ID of the collection.
            query_expr: The samples to export. None exports all samples of the collection.
                The order and the slice of a query are not sent.
            export_format: The format of the export.
            output_path: The file or folder to write. The format sets which one.
            annotation_collection_id: The annotation collection to export. None exports
                all annotations.
        """
