"""Export of an image dataset query through the active transport."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from uuid import UUID

from sqlmodel import Session
from typing_extensions import override  # typing.override needs Python 3.12.

from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.export import dataset_export, image_dataset_export
from lightly_studio.export.image_dataset_export import ImageDatasetExport
from lightly_studio.models.export_format import ExportFormat
from lightly_studio.transport import active_transport
from lightly_studio.type_definitions import PathLike


class TransportImageDatasetExport(ImageDatasetExport):
    """Exports the samples of a query through the active transport.

    A query that the transport cannot send, or that has its own session, is exported with the
    database session.
    """

    def __init__(self, session: Session, dataset_id: UUID, query: DatasetQuery) -> None:
        """Create the export for the samples of a query."""
        super().__init__(session=session, dataset_id=dataset_id, samples=query)
        self._query = query

    @override
    def to_coco_object_detections(
        self, output_json: PathLike | None = None, annotation_collection_id: UUID | None = None
    ) -> None:
        if output_json is None:
            output_json = dataset_export.DEFAULT_EXPORT_FILENAME
        self._export(
            export_format=ExportFormat.OBJECT_DETECTION_COCO,
            output_path=output_json,
            annotation_collection_id=annotation_collection_id,
            export_locally=super().to_coco_object_detections,
        )

    @override
    def to_yolo_object_detections(
        self, output_folder: PathLike, annotation_collection_id: UUID | None = None
    ) -> None:
        self._export(
            export_format=ExportFormat.OBJECT_DETECTION_YOLO,
            output_path=output_folder,
            annotation_collection_id=annotation_collection_id,
            export_locally=super().to_yolo_object_detections,
        )

    @override
    def to_coco_captions(self, output_json: PathLike | None = None) -> None:
        if output_json is None:
            output_json = dataset_export.DEFAULT_EXPORT_FILENAME
        export_captions_locally = super().to_coco_captions
        self._export(
            export_format=ExportFormat.CAPTION_COCO,
            output_path=output_json,
            annotation_collection_id=None,
            export_locally=lambda output_path, _: export_captions_locally(output_json=output_path),
        )

    @override
    def to_coco_instance_segmentation(
        self, output_json: PathLike | None = None, annotation_collection_id: UUID | None = None
    ) -> None:
        if output_json is None:
            output_json = dataset_export.DEFAULT_EXPORT_FILENAME
        self._export(
            export_format=ExportFormat.SEGMENTATION_MASK_COCO,
            output_path=output_json,
            annotation_collection_id=annotation_collection_id,
            export_locally=super().to_coco_instance_segmentation,
        )

    @override
    def to_yolo_instance_segmentation(
        self, output_folder: PathLike, annotation_collection_id: UUID | None = None
    ) -> None:
        self._export(
            export_format=ExportFormat.INSTANCE_SEGMENTATION_YOLO,
            output_path=output_folder,
            annotation_collection_id=annotation_collection_id,
            export_locally=super().to_yolo_instance_segmentation,
        )

    @override
    def to_pascalvoc_segmentation_mask(
        self, output_folder: PathLike, annotation_collection_id: UUID | None = None
    ) -> None:
        self._export(
            export_format=ExportFormat.PASCAL_VOC,
            output_path=output_folder,
            annotation_collection_id=annotation_collection_id,
            export_locally=super().to_pascalvoc_segmentation_mask,
        )

    @override
    def to_csv_classifications(
        self, output_csv: PathLike | None = None, annotation_collection_id: UUID | None = None
    ) -> None:
        if output_csv is None:
            output_csv = image_dataset_export.DEFAULT_CLASSIFICATION_EXPORT_FILENAME
        self._export(
            export_format=ExportFormat.CLASSIFICATION_CSV,
            output_path=output_csv,
            annotation_collection_id=annotation_collection_id,
            export_locally=super().to_csv_classifications,
        )

    def _export(
        self,
        export_format: ExportFormat,
        output_path: PathLike,
        annotation_collection_id: UUID | None,
        export_locally: Callable[[PathLike, UUID | None], None],
    ) -> None:
        """Export through the active transport, or with SQL if the transport cannot send the query.

        Raises:
            UnsupportedQueryError: If the transport is remote and cannot send the query.
        """
        request = self._query._export_request()  # noqa: SLF001
        # The transport cannot use the session of the query.
        has_own_session = self._query._session is not None  # noqa: SLF001
        if request is None or has_own_session:
            export_locally(output_path, annotation_collection_id)
            return
        active_transport.get_transport().export.export(
            collection_id=self._query.dataset.collection_id,
            query_expr=request.query_expr,
            export_format=export_format,
            output_path=Path(output_path),
            annotation_collection_id=annotation_collection_id,
        )
