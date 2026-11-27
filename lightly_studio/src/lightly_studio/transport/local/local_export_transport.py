"""Export transport that calls the exporters in the same process."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from uuid import UUID

# Import the module, not the class: `core` imports this module while `image_sample` loads.
from lightly_studio.core.image import image_sample
from lightly_studio.database import db_manager
from lightly_studio.errors import NotFoundError
from lightly_studio.export.image_dataset_export import ImageDatasetExport
from lightly_studio.models.collection import SampleType
from lightly_studio.models.export_format import ExportFormat
from lightly_studio.models.export_task import ExportTask
from lightly_studio.models.sample_query import SampleQueryRequest
from lightly_studio.resolvers import collection_resolver
from lightly_studio.services.sample_services import sample_query_service

_IMAGE_EXPORTS: dict[ExportFormat, Callable[[ImageDatasetExport, Path, UUID | None], None]] = {
    ExportFormat.CLASSIFICATION_CSV: ImageDatasetExport.to_csv_classifications,
    ExportFormat.OBJECT_DETECTION_COCO: ImageDatasetExport.to_coco_object_detections,
    ExportFormat.OBJECT_DETECTION_YOLO: ImageDatasetExport.to_yolo_object_detections,
    ExportFormat.SEGMENTATION_MASK_COCO: ImageDatasetExport.to_coco_instance_segmentation,
    ExportFormat.INSTANCE_SEGMENTATION_YOLO: ImageDatasetExport.to_yolo_instance_segmentation,
    ExportFormat.PASCAL_VOC: ImageDatasetExport.to_pascalvoc_segmentation_mask,
}


class LocalExportTransport:
    """Implements `ExportTransport` with the persistent database session."""

    def export(
        self, collection_id: UUID, request: SampleQueryRequest, limit: int | None, task: ExportTask
    ) -> None:
        """Export the image samples of a collection to a file or folder.

        Raises:
            NotFoundError: If the collection does not exist.
            ValueError: If the collection is not an image collection or the format is not
                supported for images.
            QueryExprError: If the query uses a field that is not valid for images.
        """
        export_samples = _IMAGE_EXPORTS.get(task.export_format)
        if export_samples is None:
            raise ValueError(
                f"Export format '{task.export_format.value}' is not supported for images."
            )
        session = db_manager.persistent_session()
        collection = collection_resolver.get_by_id(session=session, collection_id=collection_id)
        if collection is None:
            raise NotFoundError(f"Collection {collection_id} does not exist.")
        if collection.sample_type != SampleType.IMAGE:
            raise ValueError(f"Collection {collection_id} is not an image collection.")
        images = sample_query_service.get_images(
            session=session, collection_id=collection_id, request=request, limit=limit
        )
        exporter = ImageDatasetExport(
            session=session,
            dataset_id=collection.dataset_id,
            samples=[image_sample.ImageSample(inner=image) for image in images],
        )
        export_samples(exporter, task.output_path, task.annotation_collection_id)
