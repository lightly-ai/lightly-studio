"""API routes for exporting collection annotation tasks."""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path as PathlibPath
from tempfile import TemporaryDirectory

from fastapi import APIRouter, Depends, Path
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel
from sqlmodel import Field
from typing_extensions import Annotated

from lightly_studio.api.routes.api import collection as collection_api
from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.db_manager import SessionDep
from lightly_studio.export import export_dataset
from lightly_studio.models.collection import CollectionTable
from lightly_studio.resolvers import collection_resolver
from lightly_studio.resolvers.collection_resolver.export import ExportFilter

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
    dataset_query = DatasetQuery(dataset=collection, session=session)

    # Create the export in a temporary directory. We cannot use a context manager
    # because the directory should be deleted only after the file has finished streaming.
    temp_dir = TemporaryDirectory()
    output_path = PathlibPath(temp_dir.name) / "coco_export.json"

    try:
        export_dataset.to_coco_object_detections(
            session=session,
            root_dataset_id=collection.collection_id,
            samples=dataset_query,
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
    dataset_query = DatasetQuery(dataset=collection, session=session)

    # Create the export in a temporary directory. We cannot use a context manager
    # because the directory should be deleted only after the file has finished streaming.
    temp_dir = TemporaryDirectory()
    output_path = PathlibPath(temp_dir.name) / "coco_captions_export.json"

    try:
        export_dataset.to_coco_captions(
            samples=dataset_query,
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


class ExportBody(BaseModel):
    """body parameters for including or excluding tag_ids or sample_ids."""

    include: ExportFilter | None = Field(
        None, description="include filter for sample_ids or tag_ids"
    )
    exclude: ExportFilter | None = Field(
        None, description="exclude filter for sample_ids or tag_ids"
    )


# This endpoint should be a GET, however due to the potential huge size
# of sample_ids, it is a POST request to avoid URL length limitations.
# A body with a GET request is supported by fastAPI however it has undefined
# behavior: https://fastapi.tiangolo.com/tutorial/body/
@export_router.post(
    "/export",
)
def export_collection_to_absolute_paths(
    session: SessionDep,
    collection: Annotated[
        CollectionTable,
        Path(title="collection Id"),
        Depends(collection_api.get_and_validate_collection_id),
    ],
    body: ExportBody,
) -> PlainTextResponse:
    """Export collection from the database."""
    # export collection to absolute paths
    exported = collection_resolver.export(
        session=session,
        collection_id=collection.collection_id,
        include=body.include,
        exclude=body.exclude,
    )

    # Create a response with the exported data
    response = PlainTextResponse("\n".join(exported))

    # Add the Content-Disposition header to force download
    filename = f"{collection.name}_exported_{datetime.now(timezone.utc)}.txt"
    response.headers["Access-Control-Expose-Headers"] = "Content-Disposition"
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"

    return response


@export_router.post(
    "/export/stats",
)
def export_collection_stats(
    session: SessionDep,
    collection: Annotated[
        CollectionTable,
        Path(title="collection Id"),
        Depends(collection_api.get_and_validate_collection_id),
    ],
    body: ExportBody,
) -> int:
    """Get statistics about the export query."""
    return collection_resolver.get_filtered_samples_count(
        session=session,
        collection_id=collection.collection_id,
        include=body.include,
        exclude=body.exclude,
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
