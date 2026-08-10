"""API routes for exporting collection annotations."""

from __future__ import annotations

import logging
import shutil
import tempfile
from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path as PathlibPath
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Field, Session

from lightly_studio.api.routes.api import collection as collection_api
from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.core.video.video_sample import VideoSample
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.errors import NotFoundError
from lightly_studio.export import image_dataset_export, video_dataset_export
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.models.export_format import ExportFormat
from lightly_studio.resolvers import collection_resolver, export_job_resolver
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter

export_router = APIRouter(prefix="/collections/{collection_id}", tags=["export"])
_STREAM_CHUNK_SIZE_BYTES = 64 * 1024
logger = logging.getLogger(__name__)


class ExportBody(BaseModel):
    """Body parameters for exporting samples."""

    collection_filter: ImageFilter | None = Field(
        None, description="Active view filter for selecting samples to export."
    )


class ExportKeyResponse(BaseModel):
    """Response body for all prepare endpoints."""

    export_key: UUID


class ExportYoutubeVisPrepareBody(BaseModel):
    """Request body for the YouTube-VIS prepare endpoint."""

    video_filter: VideoFilter | None = None


class ExportAnnotationsPrepareBody(BaseModel):
    """Request body for the annotations prepare endpoint."""

    export_format: ExportFormat = ExportFormat.OBJECT_DETECTION_COCO
    annotation_collection_id: UUID | None = None
    image_filter: ImageFilter | None = None
    video_filter: VideoFilter | None = None


class ExportCaptionsPrepareBody(BaseModel):
    """Request body for the captions prepare endpoint."""

    image_filter: ImageFilter | None = None


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
        collection_filter=body.collection_filter,
    )


@export_router.post("/export/prepare")
def export_collection_prepare(
    collection: Annotated[
        CollectionTable,
        Path(title="collection Id"),
        Depends(collection_api.get_and_validate_collection_id),
    ],
    session: SessionDep,
    body: ExportBody,
) -> ExportKeyResponse:
    """Generate the filename export and persist its path."""
    exported = collection_resolver.export(
        session=session,
        collection_id=collection.collection_id,
        collection_filter=body.collection_filter,
    )

    temp_dir = PathlibPath(tempfile.mkdtemp())
    filename = f"{collection.name}_exported_{datetime.now(timezone.utc)}.txt"
    output_path = temp_dir / filename
    try:
        output_path.write_text("\n".join(exported))
        export = export_job_resolver.create(session=session, export_path=str(output_path))
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
    return ExportKeyResponse(export_key=export.export_key)


@export_router.post("/export/youtube-vis/prepare")
def export_collection_youtube_vis_prepare(
    collection: Annotated[
        CollectionTable,
        Path(title="collection Id"),
        Depends(collection_api.get_and_validate_collection_id),
    ],
    session: SessionDep,
    body: ExportYoutubeVisPrepareBody,
) -> ExportKeyResponse:
    """Generate the YouTube-VIS export and persist its path."""
    if collection.sample_type != SampleType.VIDEO:
        raise ValueError("YouTube-VIS export is only supported for video collections.")

    dataset_query = DatasetQuery(dataset=collection, session=session, sample_class=VideoSample)
    if body.video_filter is not None:
        dataset_query.filter_by_sample_ids(
            body.video_filter.build_sample_ids_query(collection.collection_id)
        )

    temp_dir = PathlibPath(tempfile.mkdtemp())
    output_path = temp_dir / "youtube_vis_segmentation_mask_export.json"
    try:
        video_dataset_export.to_youtube_vis_segmentation_mask(
            session=session,
            samples=dataset_query,
            output_json=output_path,
        )
        export = export_job_resolver.create(session=session, export_path=str(output_path))
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise

    return ExportKeyResponse(export_key=export.export_key)


@export_router.post("/export/annotations/prepare")
def export_collection_annotations_prepare(
    collection: Annotated[
        CollectionTable,
        Path(title="collection Id"),
        Depends(collection_api.get_and_validate_collection_id),
    ],
    session: SessionDep,
    body: ExportAnnotationsPrepareBody,
) -> ExportKeyResponse:
    """Generate the annotations export and persist its path."""
    if body.export_format == ExportFormat.YOUTUBE_VIS_SEGMENTATION:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Export format '{body.export_format.value}' is not supported for this endpoint."
            ),
        )

    exporter = _annotations_exporter(
        collection=collection,
        session=session,
        image_filter=body.image_filter,
        video_filter=body.video_filter,
    )

    temp_dir = PathlibPath(tempfile.mkdtemp())
    try:
        export_path = _generate_annotations_export(
            exporter=exporter,
            export_format=body.export_format,
            annotation_collection_id=body.annotation_collection_id,
            temp_dir=temp_dir,
        )
        export = export_job_resolver.create(session=session, export_path=str(export_path))
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise

    return ExportKeyResponse(export_key=export.export_key)


@export_router.post("/export/captions/prepare")
def export_collection_captions_prepare(
    collection: Annotated[
        CollectionTable,
        Path(title="collection Id"),
        Depends(collection_api.get_and_validate_collection_id),
    ],
    session: SessionDep,
    body: ExportCaptionsPrepareBody,
) -> ExportKeyResponse:
    """Generate the captions export and persist its path."""
    dataset_query = DatasetQuery(dataset=collection, session=session)
    if body.image_filter is not None:
        dataset_query.filter_by_sample_ids(
            body.image_filter.build_sample_ids_query(collection.collection_id)
        )

    temp_dir = PathlibPath(tempfile.mkdtemp())
    output_path = temp_dir / "coco_captions_export.json"
    try:
        image_dataset_export.ImageDatasetExport(
            session=session,
            dataset_id=collection.dataset_id,
            samples=dataset_query,
        ).to_coco_captions(output_json=output_path)
        export = export_job_resolver.create(session=session, export_path=str(output_path))
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise

    return ExportKeyResponse(export_key=export.export_key)


@export_router.get("/export/download/{export_key}")
def export_download(
    _collection: Annotated[
        CollectionTable,
        Path(title="collection Id"),
        Depends(collection_api.get_and_validate_collection_id),
    ],
    session: SessionDep,
    export_key: UUID,
) -> StreamingResponse:
    """Stream the export identified by *export_key*."""
    job = export_job_resolver.get(session=session, export_key=export_key)
    if job is None:
        raise NotFoundError("Export key not found.")

    export_path = PathlibPath(job.export_path)
    if not export_path.exists():
        raise NotFoundError("Export file not found.")
    if export_path.is_dir():
        return StreamingResponse(
            content=_stream_dir_and_cleanup(export_path, session=session, export_key=export_key),
            media_type="application/zip",
            headers={
                "Access-Control-Expose-Headers": "Content-Disposition",
                "Content-Disposition": f"attachment; filename={export_path.name}.zip",
            },
        )
    return StreamingResponse(
        content=_stream_file_and_cleanup(export_path, session=session, export_key=export_key),
        media_type=_media_type_for_path(export_path),
        headers={
            "Access-Control-Expose-Headers": "Content-Disposition",
            "Content-Disposition": f"attachment; filename={export_path.name}",
        },
    )


def _generate_annotations_export(
    exporter: image_dataset_export.ImageDatasetExport | video_dataset_export.VideoDatasetExport,
    export_format: ExportFormat,
    annotation_collection_id: UUID | None,
    temp_dir: PathlibPath,
) -> PathlibPath:
    """Run the annotations export and return the output path."""
    if export_format == ExportFormat.CLASSIFICATION_CSV:
        output_path = temp_dir / "classification_export.csv"
        exporter.to_csv_classifications(
            output_csv=output_path,
            annotation_collection_id=annotation_collection_id,
        )
        return output_path
    if not isinstance(exporter, image_dataset_export.ImageDatasetExport):
        raise ValueError(f"Export format '{export_format.value}' is only supported for images.")
    if export_format == ExportFormat.OBJECT_DETECTION_COCO:
        output_path = temp_dir / "coco_export.json"
        exporter.to_coco_object_detections(
            output_json=output_path,
            annotation_collection_id=annotation_collection_id,
        )
        return output_path
    if export_format == ExportFormat.OBJECT_DETECTION_YOLO:
        output_path = temp_dir / "yolo"
        exporter.to_yolo_object_detections(
            output_folder=output_path,
            annotation_collection_id=annotation_collection_id,
        )
        return output_path
    if export_format == ExportFormat.SEGMENTATION_MASK_COCO:
        output_path = temp_dir / "coco_segmentation_mask_export.json"
        exporter.to_coco_segmentation_masks(
            output_json=output_path,
            annotation_collection_id=annotation_collection_id,
        )
        return output_path
    if export_format == ExportFormat.PASCAL_VOC:
        output_path = temp_dir / "pascalvoc"
        exporter.to_pascalvoc_segmentation_mask(
            output_folder=output_path,
            annotation_collection_id=annotation_collection_id,
        )
        return output_path
    raise ValueError(f"Export format '{export_format.value}' is not supported for this endpoint.")


def _annotations_exporter(
    collection: CollectionTable,
    session: Session,
    image_filter: ImageFilter | None = None,
    video_filter: VideoFilter | None = None,
) -> image_dataset_export.ImageDatasetExport | video_dataset_export.VideoDatasetExport:
    """Create the annotations exporter and apply the collection's active filter."""
    if collection.sample_type == SampleType.VIDEO:
        video_query = DatasetQuery(
            dataset=collection,
            session=session,
            sample_class=VideoSample,
        )
        if video_filter is not None:
            video_query.filter_by_sample_ids(
                video_filter.build_sample_ids_query(collection.collection_id)
            )
        return video_dataset_export.VideoDatasetExport(
            session=session,
            samples=video_query,
        )

    image_query = DatasetQuery(dataset=collection, session=session)
    if image_filter is not None:
        image_query.filter_by_sample_ids(
            image_filter.build_sample_ids_query(collection.collection_id)
        )
    return image_dataset_export.ImageDatasetExport(
        session=session,
        dataset_id=collection.dataset_id,
        samples=image_query,
    )


def _stream_file_and_cleanup(
    export_path: PathlibPath,
    session: Session,
    export_key: UUID,
) -> Generator[bytes, None, None]:
    """Stream a file, remove it, and delete the DB row afterwards."""
    try:
        with export_path.open("rb") as file:
            while chunk := file.read(_STREAM_CHUNK_SIZE_BYTES):
                yield chunk
    finally:
        export_path.unlink(missing_ok=True)
        try:
            export_job_resolver.delete(session=session, export_key=export_key)
        except Exception as exc:
            logger.error(
                "Failed to delete export job %s from database: %s", export_key, exc, exc_info=True
            )


def _stream_dir_and_cleanup(
    dir_path: PathlibPath,
    session: Session,
    export_key: UUID,
) -> Generator[bytes, None, None]:
    """Zip the export directory, stream the archive, remove both, and delete the DB row."""
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
        shutil.rmtree(dir_path, ignore_errors=True)
        try:
            export_job_resolver.delete(session=session, export_key=export_key)
        except Exception as exc:
            logger.error(
                "Failed to delete export job %s from database: %s", export_key, exc, exc_info=True
            )
        raise
    shutil.rmtree(dir_path, ignore_errors=True)
    yield from _stream_file_and_cleanup(
        export_path=archive_path, session=session, export_key=export_key
    )


def _media_type_for_path(path: PathlibPath) -> str:
    if path.suffix == ".csv":
        return "text/csv"
    if path.suffix == ".json":
        return "application/json"
    if path.suffix == ".txt":
        return "text/plain"
    return "application/octet-stream"
