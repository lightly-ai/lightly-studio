from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.core.dataset_query import ImageSampleField, OrderByField
from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.core.image.image_dataset import ImageDataset
from lightly_studio.core.image.transport_image_dataset_export import TransportImageDatasetExport
from lightly_studio.export.image_dataset_export import ImageDatasetExport
from lightly_studio.models.export_format import ExportFormat
from lightly_studio.models.query_expr import (
    FieldRef,
    IntegerExpr,
    OrdinalComparisonOperator,
    QueryExpr,
)
from lightly_studio.transport import active_transport
from lightly_studio.transport.local.local_export_transport import LocalExportTransport
from tests.helpers_resolvers import create_collection, create_image


@pytest.mark.usefixtures("patch_collection")
class TestTransportImageDatasetExport:
    @pytest.mark.parametrize(
        ("export_samples", "export_format", "annotation_collection_id"),
        [
            (
                lambda export, path, collection_id: export.to_coco_object_detections(
                    output_json=path, annotation_collection_id=collection_id
                ),
                ExportFormat.OBJECT_DETECTION_COCO,
                None,
            ),
            (
                lambda export, path, collection_id: export.to_yolo_object_detections(
                    output_folder=path, annotation_collection_id=collection_id
                ),
                ExportFormat.OBJECT_DETECTION_YOLO,
                uuid4(),
            ),
            (
                lambda export, path, collection_id: export.to_coco_instance_segmentation(
                    output_json=path, annotation_collection_id=collection_id
                ),
                ExportFormat.SEGMENTATION_MASK_COCO,
                None,
            ),
            (
                lambda export, path, collection_id: export.to_yolo_instance_segmentation(
                    output_folder=path, annotation_collection_id=collection_id
                ),
                ExportFormat.INSTANCE_SEGMENTATION_YOLO,
                uuid4(),
            ),
            (
                lambda export, path, collection_id: export.to_pascalvoc_segmentation_mask(
                    output_folder=path, annotation_collection_id=collection_id
                ),
                ExportFormat.PASCAL_VOC,
                None,
            ),
            (
                lambda export, path, collection_id: export.to_csv_classifications(
                    output_csv=path, annotation_collection_id=collection_id
                ),
                ExportFormat.CLASSIFICATION_CSV,
                uuid4(),
            ),
        ],
    )
    def test_export(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        export_samples: Callable[[TransportImageDatasetExport, Path, UUID | None], None],
        export_format: ExportFormat,
        annotation_collection_id: UUID | None,
    ) -> None:
        dataset = ImageDataset.create(name="test_dataset")
        query = dataset.match(ImageSampleField.width > 10)
        transport = mocker.patch.object(active_transport, "get_transport").return_value
        export = TransportImageDatasetExport(
            session=dataset.session, dataset_id=dataset.dataset_id, query=query
        )

        export_samples(export, tmp_path / "export", annotation_collection_id)

        transport.export.export.assert_called_once_with(
            collection_id=dataset.collection_id,
            query_expr=QueryExpr(
                match_expr=IntegerExpr(
                    field=FieldRef(table="image", name="width"),
                    operator=OrdinalComparisonOperator.GT,
                    value=10,
                )
            ),
            export_format=export_format,
            output_path=tmp_path / "export",
            annotation_collection_id=annotation_collection_id,
        )

    @pytest.mark.parametrize(
        ("export_samples", "output_path"),
        [
            (lambda export: export.to_coco_object_detections(), Path("coco_export.json")),
            (lambda export: export.to_coco_instance_segmentation(), Path("coco_export.json")),
            (lambda export: export.to_csv_classifications(), Path("classification_export.csv")),
        ],
    )
    def test_export__default_path(
        self,
        mocker: MockerFixture,
        export_samples: Callable[[TransportImageDatasetExport], None],
        output_path: Path,
    ) -> None:
        dataset = ImageDataset.create(name="test_dataset")
        transport = mocker.patch.object(active_transport, "get_transport").return_value

        export_samples(
            TransportImageDatasetExport(
                session=dataset.session, dataset_id=dataset.dataset_id, query=dataset.query()
            )
        )

        assert transport.export.export.call_args.kwargs["output_path"] == output_path

    @pytest.mark.parametrize(
        ("export_samples", "local_export_method"),
        [
            (
                lambda export, path: export.to_coco_object_detections(output_json=path),
                "to_coco_object_detections",
            ),
            (
                lambda export, path: export.to_yolo_object_detections(output_folder=path),
                "to_yolo_object_detections",
            ),
            (
                lambda export, path: export.to_coco_instance_segmentation(output_json=path),
                "to_coco_instance_segmentation",
            ),
            (
                lambda export, path: export.to_yolo_instance_segmentation(output_folder=path),
                "to_yolo_instance_segmentation",
            ),
            (
                lambda export, path: export.to_pascalvoc_segmentation_mask(output_folder=path),
                "to_pascalvoc_segmentation_mask",
            ),
            (
                lambda export, path: export.to_csv_classifications(output_csv=path),
                "to_csv_classifications",
            ),
        ],
    )
    def test_export__ordered_query(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        export_samples: Callable[[TransportImageDatasetExport, Path], None],
        local_export_method: str,
    ) -> None:
        dataset = ImageDataset.create(name="test_dataset")
        query = dataset.query().order_by(OrderByField(ImageSampleField.width))
        export_locally = mocker.patch.object(ImageDatasetExport, local_export_method)
        transport_export = mocker.spy(LocalExportTransport, "export")

        export_samples(
            TransportImageDatasetExport(
                session=dataset.session, dataset_id=dataset.dataset_id, query=query
            ),
            tmp_path / "export",
        )

        export_locally.assert_called_once_with(tmp_path / "export", None)
        transport_export.assert_not_called()

    def test_export__ordered_query__sample_order(self, tmp_path: Path) -> None:
        dataset = ImageDataset.create(name="test_dataset")
        create_image(
            session=dataset.session,
            collection_id=dataset.collection_id,
            file_path_abs="/a.png",
            width=20,
        )
        create_image(
            session=dataset.session,
            collection_id=dataset.collection_id,
            file_path_abs="/b.png",
            width=10,
        )
        query = dataset.query().order_by(OrderByField(ImageSampleField.width))

        TransportImageDatasetExport(
            session=dataset.session, dataset_id=dataset.dataset_id, query=query
        ).to_coco_object_detections(output_json=tmp_path / "coco.json")

        coco = json.loads((tmp_path / "coco.json").read_text())
        assert [image["file_name"] for image in coco["images"]] == ["/b.png", "/a.png"]

    def test_export__query_with_session(
        self, mocker: MockerFixture, tmp_path: Path, db_session: Session
    ) -> None:
        collection = create_collection(session=db_session)
        query = DatasetQuery(dataset=collection, session=db_session)
        query.match(ImageSampleField.width > 10)
        export_locally = mocker.patch.object(ImageDatasetExport, "to_coco_object_detections")
        transport = mocker.patch.object(active_transport, "get_transport").return_value

        TransportImageDatasetExport(
            session=db_session, dataset_id=collection.dataset_id, query=query
        ).to_coco_object_detections(output_json=tmp_path / "coco.json")

        export_locally.assert_called_once_with(tmp_path / "coco.json", None)
        transport.export.export.assert_not_called()
