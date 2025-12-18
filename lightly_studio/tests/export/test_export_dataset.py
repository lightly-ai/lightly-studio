from __future__ import annotations

import json
from pathlib import Path

from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.core.dataset import Dataset
from lightly_studio.core.dataset_query import SampleField
from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.export import export_dataset
from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationType
from lightly_studio.models.collection import CollectionTable
from lightly_studio.resolvers import annotation_resolver
from tests.helpers_resolvers import (
    ImageStub,
    create_annotation_label,
    create_caption,
    create_dataset,
    create_images,
)


class TestDatasetExport:
    def test_to_coco_object_detections(
        self,
        tmp_path: Path,
        patch_dataset: None,  # noqa: ARG002
    ) -> None:
        """Tests DatasetExport exporting to COCO format."""
        dataset = Dataset.create(name="test_dataset")
        images_to_create = [
            ImageStub(path="image0.jpg", width=100, height=100),
            ImageStub(path="image1.jpg", width=200, height=200),
            ImageStub(path="image2.jpg", width=300, height=300),
        ]
        images = create_images(
            db_session=db_session, dataset_id=dataset.collection_id, images=images_to_create
        )
        label = create_annotation_label(session=dataset.session, annotation_label_name="dog")
        # TODO(lukas 9/2025): make this into a function
        annotation_resolver.create_many(
            session=dataset.session,
            parent_dataset_id=dataset.collection_id,
            annotations=[
                AnnotationCreate(
                    parent_sample_id=images[0].sample_id,
                    annotation_label_id=label.annotation_label_id,
                    annotation_type=AnnotationType.OBJECT_DETECTION,
                    confidence=None,
                    x=10,
                    y=10,
                    width=10,
                    height=10,
                ),
            ],
        )

        output_json = tmp_path / "task_obj_det_1.json"
        query = dataset.query().match(SampleField.height <= 200)
        dataset.export(query).to_coco_object_detections(output_json=output_json)

        # Load the generated JSON and verify its content
        with open(output_json) as f:
            coco_data = json.load(f)
        # Last image is not included due to filtered out height
        assert coco_data == {
            "images": [
                {"id": 0, "file_name": "image0.jpg", "width": 100, "height": 100},
                {"id": 1, "file_name": "image1.jpg", "width": 200, "height": 200},
            ],
            "categories": [{"id": 0, "name": "dog"}],
            "annotations": [
                {"image_id": 0, "category_id": 0, "bbox": [10.0, 10.0, 10.0, 10.0]},
            ],
        }

    def test_to_coco_object_detections__str_path(
        self,
        tmp_path: Path,
        patch_dataset: None,  # noqa: ARG002
    ) -> None:
        """Tests DatasetExport exporting to COCO format."""
        dataset = Dataset.create(name="test_dataset")
        images = [ImageStub(path="image0.jpg", width=100, height=100)]
        create_images(db_session=dataset.session, dataset_id=dataset.collection_id, images=images)

        output_json = tmp_path / "export.json"
        # Provide the export path as a string
        dataset.export().to_coco_object_detections(output_json=str(output_json))

        # Verify the file exists
        assert output_json.exists()

    def test_to_coco_object_detections__default_path(
        self,
        mocker: MockerFixture,
        patch_dataset: None,  # noqa: ARG002
    ) -> None:
        dataset = Dataset.create(name="test_dataset")

        # Mock the actual export function to avoid creating a file
        mock_to_coco_object_detections = mocker.patch.object(
            export_dataset, "to_coco_object_detections"
        )

        # Don't provide the export path
        dataset.export().to_coco_object_detections()

        # Check that a default output path was used
        mock_to_coco_object_detections.assert_called_once_with(
            session=dataset.session,
            samples=mocker.ANY,
            output_json=Path("coco_export.json"),
        )

    def test_to_coco_captions(
        self,
        tmp_path: Path,
        patch_dataset: None,  # noqa: ARG002
    ) -> None:
        dataset = Dataset.create(name="test_dataset")
        image = create_images(
            db_session=dataset.session,
            dataset_id=dataset.collection_id,
            images=[ImageStub(path="/path/image0.jpg", width=100, height=100)],
        )[0]
        create_caption(
            session=dataset.session,
            dataset_id=dataset.collection_id,
            parent_sample_id=image.sample_id,
            text="caption one",
        )

        # Call the function under test
        output_json = tmp_path / "coco_annotations.json"
        dataset.export().to_coco_captions(output_json=output_json)

        # Load the generated JSON and verify its content
        with open(output_json) as f:
            coco_data = json.load(f)
        assert coco_data == {
            "images": [
                {"id": 0, "file_name": "/path/image0.jpg", "width": 100, "height": 100},
            ],
            "annotations": [
                {"id": 0, "image_id": 0, "caption": "caption one"},
            ],
        }

    def test_to_coco_captions__str_path(
        self,
        tmp_path: Path,
        patch_dataset: None,  # noqa: ARG002
    ) -> None:
        dataset = Dataset.create(name="test_dataset")

        # Call the function under test
        output_json = tmp_path / "coco_annotations.json"
        dataset.export().to_coco_captions(output_json=str(output_json))

        assert output_json.exists()

    def test_to_coco_captions__default_path(
        self,
        mocker: MockerFixture,
        patch_dataset: None,  # noqa: ARG002
    ) -> None:
        mock_to_coco_captions = mocker.patch.object(export_dataset, "to_coco_captions")

        dataset = Dataset.create(name="test_dataset")

        # Call the function under test
        dataset.export().to_coco_captions()

        # Check that a default output path was used
        mock_to_coco_captions.assert_called_once_with(
            samples=mocker.ANY,
            output_json=Path("coco_export.json"),
        )


def test_to_coco_object_detections(
    db_session: Session,
    dataset_with_annotations: CollectionTable,
    tmp_path: Path,
) -> None:
    """Tests exporting to COCO format."""
    dataset = dataset_with_annotations

    # Test for task_obj_det_1
    output_json = tmp_path / "task_obj_det_1.json"
    export_dataset.to_coco_object_detections(
        session=db_session,
        samples=DatasetQuery(dataset=dataset, session=db_session),
        output_json=output_json,
    )

    # Load the generated JSON and verify its content
    with open(output_json) as f:
        coco_data = json.load(f)
    assert coco_data == {
        "images": [
            {"id": 0, "file_name": "img1", "width": 100, "height": 100},
            {"id": 1, "file_name": "img2", "width": 200, "height": 200},
            {"id": 2, "file_name": "img3", "width": 300, "height": 300},
        ],
        "categories": [
            {"id": 0, "name": "cat"},
            {"id": 1, "name": "dog"},
            {"id": 2, "name": "zebra"},
        ],
        "annotations": [
            {"image_id": 0, "category_id": 1, "bbox": [10.0, 10.0, 10.0, 10.0]},
            {"image_id": 0, "category_id": 0, "bbox": [20.0, 20.0, 20.0, 20.0]},
            {"image_id": 1, "category_id": 1, "bbox": [30.0, 30.0, 30.0, 30.0]},
        ],
    }


def test_to_coco_object_detections__no_annotations(
    db_session: Session,
    tmp_path: Path,
) -> None:
    """Tests exporting to COCO format - no annotations."""
    dataset = create_dataset(session=db_session)
    images = [
        ImageStub(path="img1", width=100, height=100),
        ImageStub(path="img2", width=200, height=200),
    ]
    create_images(db_session=db_session, dataset_id=dataset.collection_id, images=images)

    output_json = tmp_path / "task_no_ann.json"
    export_dataset.to_coco_object_detections(
        session=db_session,
        samples=DatasetQuery(dataset=dataset, session=db_session),
        output_json=output_json,
    )

    # Load the generated JSON and verify its content
    with open(output_json) as f:
        coco_data = json.load(f)
    assert coco_data == {
        "images": [
            {"id": 0, "file_name": "img1", "width": 100, "height": 100},
            {"id": 1, "file_name": "img2", "width": 200, "height": 200},
        ],
        "categories": [],
        "annotations": [],
    }


def test_to_coco_captions(
    db_session: Session,
    tmp_path: Path,
) -> None:
    dataset = create_dataset(session=db_session)
    image = create_images(
        db_session=db_session,
        dataset_id=dataset.collection_id,
        images=[ImageStub(path="/path/image0.jpg", width=100, height=100)],
    )[0]
    create_caption(
        session=db_session,
        dataset_id=dataset.collection_id,
        parent_sample_id=image.sample_id,
        text="caption one",
    )

    # Call the function under test
    output_json = tmp_path / "coco_annotations.json"
    export_dataset.to_coco_captions(
        samples=DatasetQuery(dataset=dataset, session=db_session),
        output_json=output_json,
    )

    # Load the generated JSON and verify its content
    with open(output_json) as f:
        coco_data = json.load(f)
    assert coco_data == {
        "images": [
            {"id": 0, "file_name": "/path/image0.jpg", "width": 100, "height": 100},
        ],
        "annotations": [
            {"id": 0, "image_id": 0, "caption": "caption one"},
        ],
    }
