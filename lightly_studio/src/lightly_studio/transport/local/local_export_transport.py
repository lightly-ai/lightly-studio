"""Export transport that calls the exporters in the same process."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from uuid import UUID

# Import the module, not the class: `core` imports this module while `dataset_query` loads.
from lightly_studio.core.dataset_query import dataset_query
from lightly_studio.database import db_manager
from lightly_studio.errors import NotFoundError
from lightly_studio.export.image_dataset_export import ImageDatasetExport
from lightly_studio.models.collection import SampleType
from lightly_studio.models.export_format import ExportFormat
from lightly_studio.models.query_expr import QueryExpr
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
        self,
        collection_id: UUID,
        query_expr: QueryExpr | None,
        export_format: ExportFormat,
        output_path: Path,
        annotation_collection_id: UUID | None,
    ) -> None:
        """Export the image samples of a collection to a file or folder.

        Raises:
            NotFoundError: If the collection does not exist.
            ValueError: If the collection is not an image collection or the format is not
                supported for images.
            QueryExprError: If the query uses a field that is not valid for images.
        """
        export_samples = _IMAGE_EXPORTS.get(export_format)
        if export_samples is None:
            raise ValueError(f"Export format '{export_format.value}' is not supported for images.")
        session = db_manager.persistent_session()
        collection = collection_resolver.get_by_id(session=session, collection_id=collection_id)
        if collection is None:
            raise NotFoundError(f"Collection {collection_id} does not exist.")
        if collection.sample_type != SampleType.IMAGE:
            raise ValueError(f"Collection {collection_id} is not an image collection.")
        query = dataset_query.DatasetQuery(dataset=collection, session=session)
        if query_expr is not None:
            query.match(sample_query_service.to_image_match_expression(query_expr=query_expr))
        exporter = ImageDatasetExport(
            session=session, dataset_id=collection.dataset_id, samples=query
        )
        export_samples(exporter, output_path, annotation_collection_id)
