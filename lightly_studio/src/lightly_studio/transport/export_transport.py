"""Transport protocol for exporting samples and annotations."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol
from uuid import UUID

from lightly_studio.models.export_format import ExportFormat


class ExportTransport(Protocol):
    """Exports samples and their annotations to files."""

    def export(
        self,
        sample_ids: Sequence[UUID],
        export_format: ExportFormat,
        output_path: Path,
        annotation_collection_id: UUID | None,
    ) -> None:
        """Export samples to a file or folder on the local machine.

        Args:
            sample_ids: The samples to export.
            export_format: The format of the export.
            output_path: The file or folder to write. The format sets which one.
            annotation_collection_id: The annotation collection to export. None exports
                all annotations.
        """
