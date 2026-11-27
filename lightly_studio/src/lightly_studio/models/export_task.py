"""The export task of the export transport."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from pydantic import BaseModel

from lightly_studio.models.export_format import ExportFormat


class ExportTask(BaseModel):
    """An export to write.

    Attributes:
        export_format: The format of the export.
        output_path: The file or folder to write. The format sets which one.
        annotation_collection_id: The annotation collection to export. None exports all
            annotations.
    """

    export_format: ExportFormat
    output_path: Path
    annotation_collection_id: UUID | None
