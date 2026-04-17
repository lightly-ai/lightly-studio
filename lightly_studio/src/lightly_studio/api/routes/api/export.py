"""API routes for exporting collection annotation tasks."""

from __future__ import annotations

import shutil
from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path as PathlibPath
from tempfile import TemporaryDirectory
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel
from sqlmodel import Field

from lightly_studio.api.routes.api import collection as collection_api
from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.core.video.video_sample import VideoSample
from lightly_studio.db_manager import SessionDep
from lightly_studio.export import image_dataset_export, video_dataset_export
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.models.export_format import ExportFormat
from lightly_studio.resolvers import collection_resolver
from lightly_studio.resolvers.collection_resolver.export import ExportFilter

export_router = APIRouter(prefix="/collections/{collection_id}", tags=["export"])
_STREAM_CHUNK_SIZE_BYTES = 64 * 1024


@export_router.get("/export/annotations")
def export_collection_annotations(
    collection: Annotated[
        CollectionTable,
        Path(title="collection Id"),
        Depends(collection_api.get_and_validate_collection_id),
    ],
    session: SessionDep,
    export_format: ExportFormat = ExportFormat.OBJECT_DETECTION_COCO,
) -> StreamingResponse:
    """Export collection annotations in the selected export format."""
    # Query to export - all samples in the collection.
    dataset_query = DatasetQuery(dataset=collection, session=session)

    # Create the export in a temporary directory. We cannot use a context manager
    # because the directory should be deleted only after the file has finished streaming.
    temp_dir = TemporaryDirectory()

    if export_format == ExportFormat.OBJECT_DETECTION_COCO:
        output_path = PathlibPath(temp_dir.name) / "coco_export.json"
        try:
            image_dataset_export.to_coco_object_detections(
                session=session,
                dataset_id=collection.dataset_id,
                samples=dataset_query,
                output_json=output_path,
            )
        except Exception:
            temp_dir.cleanup()
            # Reraise.
            raise
    elif export_format == ExportFormat.SEGMENTATION_MASK_COCO:
        output_path = PathlibPath(temp_dir.name) / "coco_instance_segmentation_export.json"

        try:
            image_dataset_export.to_coco_instance_segmentations(
                session=session,
                dataset_id=collection.dataset_id,
                samples=dataset_query,
                output_json=output_path,
            )
        except Exception:
            temp_dir.cleanup()
            # Reraise.
            raise
    elif export_format == ExportFormat.PASCAL_VOC:
        output_path = PathlibPath(temp_dir.name) / "pascalvoc"

        try:
            image_dataset_export.to_pascalvoc_instance_segmentation(
                session=session,
                dataset_id=collection.dataset_id,
                samples=dataset_query,
                output_folder=output_path,
            )
        except Exception:
            temp_dir.cleanup()
            # Reraise.
            raise

        # For Pascal VOC export, the exporter produces a directory,
        # so this route should stream the folder as a .zip instead of streaming a single file.
        return StreamingResponse(
            content=_stream_export_dir(
                temp_dir=temp_dir,
                dir_path=output_path,
            ),
            media_type="application/zip",
            headers={
                "Access-Control-Expose-Headers": "Content-Disposition",
                "Content-Disposition": f"attachment; filename={output_path.name}.zip",
            },
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Export format '{export_format.value}' is not supported for this endpoint.",
        )

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
        image_dataset_export.to_coco_captions(
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
            while chunk := file.read(_STREAM_CHUNK_SIZE_BYTES):
                yield chunk
    finally:
        temp_dir.cleanup()


@export_router.get("/export/youtube-vis")
def export_collection_youtube_vis(
    collection: Annotated[
        CollectionTable,
        Path(title="collection Id"),
        Depends(collection_api.get_and_validate_collection_id),
    ],
    session: SessionDep,
    export_format: ExportFormat = ExportFormat.YOUTUBE_VIS_SEGMENTATION,
) -> StreamingResponse:
    """Export collection video annotations in the selected export format."""
    if collection.sample_type != SampleType.VIDEO:
        raise HTTPException(
            status_code=400, detail="YouTube-VIS export is only supported for video collections."
        )

    if export_format != ExportFormat.YOUTUBE_VIS_SEGMENTATION:
        raise HTTPException(
            status_code=400,
            detail="Only YouTube-VIS segmentation format is supported for this endpoint.",
        )
    dataset_query = DatasetQuery(dataset=collection, session=session, sample_class=VideoSample)

    temp_dir = TemporaryDirectory()
    output_path = PathlibPath(temp_dir.name) / "youtube_vis_instance_segmentation_export.json"

    try:
        video_dataset_export.to_youtube_vis_instance_segmentation(
            session=session,
            samples=dataset_query,
            output_json=output_path,
        )
    except Exception:
        temp_dir.cleanup()
        raise

    return StreamingResponse(
        content=_stream_export_file(temp_dir=temp_dir, file_path=output_path),
        media_type="application/json",
        headers={
            "Access-Control-Expose-Headers": "Content-Disposition",
            "Content-Disposition": f"attachment; filename={output_path.name}",
        },
    )


def _stream_export_dir(
    temp_dir: TemporaryDirectory[str],
    dir_path: PathlibPath,
) -> Generator[bytes, None, None]:
    """Zip and stream an export directory, then clean up the temporary directory."""
    try:
        archive_path = PathlibPath(
            shutil.make_archive(
                base_name=str(dir_path),
                format="zip",
                root_dir=dir_path.parent,
                base_dir=dir_path.name,
            )
        )
    except Exception:
        temp_dir.cleanup()
        # Reraise.
        raise

    yield from _stream_export_file(temp_dir=temp_dir, file_path=archive_path)
