"""API routes for exporting collection annotation tasks."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path as PathlibPath
from tempfile import TemporaryDirectory

from fastapi import APIRouter, Depends, Path
from fastapi.responses import StreamingResponse
from typing_extensions import Annotated

from lightly_studio.api.routes.api import collection as collection_api
from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.db_manager import SessionDep
from lightly_studio.export import export_dataset
from lightly_studio.models.collection import CollectionTable

export_router = APIRouter(prefix="/collections/{collection_id}", tags=["export"])


@export_router.get("/export/annotations")
def export_collection_annotations(
    collection: Annotated[
        CollectionTable,
        Path(title="collection Id"),
        Depends(collection_api.get_and_validate_collection_id),
    ],
    session: SessionDep,
) -> StreamingResponse:
    """Export collection annotations for an object detection task in COCO format."""
    # Query to export - all samples in the collection.
    collection_query = DatasetQuery(dataset=collection, session=session)

    # Create the export in a temporary directory. We cannot use a context manager
    # because the directory should be deleted only after the file has finished streaming.
    temp_dir = TemporaryDirectory()
    output_path = PathlibPath(temp_dir.name) / "coco_export.json"

    try:
        export_dataset.to_coco_object_detections(
            session=session,
            samples=collection_query,
            output_json=output_path,
        )
    except Exception:
        temp_dir.cleanup()
        # Reraise.
        raise

    return StreamingResponse(
        content=_stream_export_file(
            temp_dir=temp_dir,
            file_path=output_path,
        ),
        media_type="application/json",
        headers={
            "Access-Control-Expose-Headers": "Content-Disposition",
            "Content-Disposition": f"attachment; filename={output_path.name}",
        },
    )


@export_router.get("/export/captions")
def export_collection_captions(
    collection: Annotated[
        CollectionTable,
        Path(title="collection Id"),
        Depends(collection_api.get_and_validate_collection_id),
    ],
    session: SessionDep,
) -> StreamingResponse:
    """Export collection captions in COCO format."""
    # Query to export - all samples in the collection.
    collection_query = DatasetQuery(dataset=collection, session=session)

    # Create the export in a temporary directory. We cannot use a context manager
    # because the directory should be deleted only after the file has finished streaming.
    temp_dir = TemporaryDirectory()
    output_path = PathlibPath(temp_dir.name) / "coco_captions_export.json"

    try:
        export_dataset.to_coco_captions(
            samples=collection_query,
            output_json=output_path,
        )
    except Exception:
        temp_dir.cleanup()
        # Reraise.
        raise

    return StreamingResponse(
        content=_stream_export_file(
            temp_dir=temp_dir,
            file_path=output_path,
        ),
        media_type="application/json",
        headers={
            "Access-Control-Expose-Headers": "Content-Disposition",
            "Content-Disposition": f"attachment; filename={output_path.name}",
        },
    )


def _stream_export_file(
    temp_dir: TemporaryDirectory[str],
    file_path: PathlibPath,
) -> Generator[bytes, None, None]:
    """Stream the export file and clean up the temporary directory afterwards."""
    try:
        with file_path.open("rb") as file:
            yield from file
    finally:
        temp_dir.cleanup()
