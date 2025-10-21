from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pytest
from labelformat.formats.coco import (
    COCOInstanceSegmentationInput,
    COCOObjectDetectionInput,
)
from labelformat.model.binary_mask_segmentation import BinaryMaskSegmentation
from labelformat.model.bounding_box import BoundingBox, BoundingBoxFormat
from labelformat.model.category import Category
from labelformat.model.image import Image
from labelformat.model.instance_segmentation import (
    ImageInstanceSegmentation,
    SingleInstanceSegmentation,
)
from labelformat.model.multipolygon import MultiPolygon
from labelformat.model.object_detection import (
    ImageObjectDetection,
    SingleObjectDetection,
)
from pytest_mock import MockerFixture
from sqlmodel import select

from lightly_studio.api.routes.api.features import lightly_studio_active_features
from lightly_studio.dataset import loader as loader_module
from lightly_studio.dataset.loader import DatasetLoader
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.embedding_model import EmbeddingModelTable
from lightly_studio.models.sample import ImageTable
from tests.conftest import assert_contains_properties


@pytest.fixture
def test_polygon_coords() -> list[tuple[float, float]]:
    return [(10.0, 0.0), (10.0, 30.0), (20.0, 30.0), (20.0, 0.0), (10.0, 0.0)]


@pytest.fixture
def test_polygon_bbox(test_polygon_coords: list[tuple[float, float]]) -> dict[str, float]:
    return {
        "x": min(coord[0] for coord in test_polygon_coords),
        "y": min(coord[1] for coord in test_polygon_coords),
        "width": max(coord[0] for coord in test_polygon_coords)
        - min(coord[0] for coord in test_polygon_coords),
        "height": max(coord[1] for coord in test_polygon_coords)
        - min(coord[1] for coord in test_polygon_coords),
    }


@pytest.fixture
def test_bounding_box() -> BoundingBox:
    return BoundingBox(5, 10, 20, 30)


class MockCOCOObjectDetectionInput(
    COCOObjectDetectionInput,
):
    """Mock class for a COCOObjectDetectionInput."""

    def __init__(self, bounding_box: BoundingBox) -> None:
        self.categories = [Category(0, "person"), Category(1, "car")]
        self.bounding_box = bounding_box

    def get_labels(self) -> Iterable[ImageObjectDetection]:
        image = Image(id=0, filename="test_image.jpg", width=640, height=480)
        objects = [SingleObjectDetection(self.categories[0], self.bounding_box)]
        return [ImageObjectDetection(image, objects)]

    def get_categories(self) -> list[Category]:
        return self.categories


class MockCOCOInstanceSegmentationInput(COCOInstanceSegmentationInput):
    """Mock class for a COCOInstanceSegmentationInput.

    Contains both polygon and binary mask segmentations.
    """

    def __init__(
        self, bounding_box: BoundingBox, polygon_coords: list[tuple[float, float]]
    ) -> None:
        self.categories = [Category(0, "person"), Category(1, "car")]
        self.bounding_box = bounding_box
        self.polygon_coords = polygon_coords

    def get_labels(self) -> Iterable[ImageInstanceSegmentation]:
        image = Image(id=0, filename="test_image.jpg", width=640, height=480)
        objects = [
            SingleInstanceSegmentation(
                self.categories[0],
                segmentation=MultiPolygon([self.polygon_coords]),
            ),
            SingleInstanceSegmentation(
                category=self.categories[1],
                segmentation=BinaryMaskSegmentation.from_binary_mask(
                    np.array([[0, 1], [1, 0]]),
                    bounding_box=self.bounding_box,
                ),
            ),
        ]
        return [ImageInstanceSegmentation(image, objects)]

    def get_categories(self) -> list[Category]:
        return self.categories


@pytest.fixture
def mock_coco_data(test_bounding_box: BoundingBox) -> MockCOCOObjectDetectionInput:
    return MockCOCOObjectDetectionInput(test_bounding_box)


class TestDatasetLoader:
    def test_from_coco_object_detections(
        self,
        patch_loader: None,  # noqa: ARG002
        mocker: MockerFixture,
        mock_coco_data: COCOObjectDetectionInput,
        test_bounding_box: BoundingBox,
    ) -> None:
        # Arrange
        data_json_path = "/fake/path/data.json"
        image_folder_path = "/fake/path/images"
        loader = DatasetLoader()
        mocker.patch.object(
            loader_module,
            "COCOObjectDetectionInput",
            return_value=mock_coco_data,
        )

        # Act
        dataset = loader.from_coco_object_detections(data_json_path, image_folder_path)
        assert dataset.name == Path(data_json_path).parent.name

        # We should set the embeddingSearchEnabled
        # if embedding_generator is provided
        assert lightly_studio_active_features == ["embeddingSearchEnabled"]

        # Assert
        session = loader.session

        # Check if labels were created
        labels = session.exec(select(AnnotationLabelTable)).all()
        assert len(labels) == 2
        assert labels[0].annotation_label_name == "person"
        assert labels[1].annotation_label_name == "car"

        # Check if sample was created
        sample = session.exec(select(ImageTable)).first()
        assert sample is not None
        assert sample.file_name == "test_image.jpg"
        assert sample.width == 640
        assert sample.height == 480

        # Check if sampleEmbedding was created
        assert sample.embeddings is not None
        embedding_model = session.exec(select(EmbeddingModelTable)).first()
        assert embedding_model is not None
        assert len(sample.embeddings[0].embedding) == embedding_model.embedding_dimension

        # Check if annotation was created
        annotation = session.exec(select(AnnotationBaseTable)).first()
        assert annotation is not None
        object_detection_details = annotation.object_detection_details
        assert object_detection_details is not None

        x, y, width, height = test_bounding_box.to_format(BoundingBoxFormat.XYWH)
        assert object_detection_details.x == x
        assert object_detection_details.y == y
        assert object_detection_details.width == width
        assert object_detection_details.height == height

    def test_from_coco_instance_segmentations(
        self,
        patch_loader: None,  # noqa: ARG002
        mocker: MockerFixture,
        test_bounding_box: BoundingBox,
        test_polygon_coords: list[tuple[float, float]],
        test_polygon_bbox: dict[str, float],
    ) -> None:
        # Clear the lightly_studio_active_features before the test
        lightly_studio_active_features.clear()

        # Arrange
        data_json_path = "/fake/path/data.json"
        image_folder_path = "/fake/path/images"
        instance_segmentation_input = MockCOCOInstanceSegmentationInput(
            test_bounding_box, test_polygon_coords
        )
        loader = DatasetLoader()
        mocker.patch.object(
            loader_module,
            "COCOInstanceSegmentationInput",
            return_value=instance_segmentation_input,
        )

        # Act
        dataset = loader.from_coco_instance_segmentations(data_json_path, image_folder_path)
        assert dataset.name == Path(data_json_path).parent.name

        # Assert
        session = loader.session

        # Check if labels were created
        labels = session.exec(select(AnnotationLabelTable)).all()
        assert len(labels) == 2
        label_names = {lbl.annotation_label_name for lbl in labels}
        assert label_names == {"person", "car"}

        # Check if sample was created
        sample = session.exec(select(ImageTable)).first()
        assert sample is not None
        assert sample.file_name == "test_image.jpg"
        assert sample.width == 640
        assert sample.height == 480

        # Check for the annotations.
        annotations = session.exec(select(AnnotationBaseTable)).all()
        assert len(annotations) == 2

        polygon_annotation = annotations[0]
        assert polygon_annotation.annotation_label.annotation_label_name == "person"
        assert polygon_annotation.instance_segmentation_details is not None
        assert_contains_properties(
            polygon_annotation.instance_segmentation_details,
            {
                **test_polygon_bbox,
                "segmentation_mask": None,
            },
        )

        mask_annotation = annotations[1]
        assert mask_annotation.annotation_label.annotation_label_name == "car"

        assert mask_annotation.instance_segmentation_details is not None
        x, y, width, height = test_bounding_box.to_format(BoundingBoxFormat.XYWH)
        assert_contains_properties(
            mask_annotation.instance_segmentation_details,
            {
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "segmentation_mask": [1, 2, 1],
            },
        )

    def test_from_coco_instance_segmentations__without_embedding_generator(
        self,
        patch_loader: None,  # noqa: ARG002
        mocker: MockerFixture,
        test_bounding_box: BoundingBox,
        test_polygon_coords: list[tuple[float, float]],
        test_polygon_bbox: dict[str, float],
    ) -> None:
        # Clear the lightly_studio_active_features before the test
        lightly_studio_active_features.clear()

        # Arrange
        data_json_path = "/fake/path/data.json"
        image_folder_path = "/fake/path/images"
        instance_segmentation_input = MockCOCOInstanceSegmentationInput(
            test_bounding_box, test_polygon_coords
        )
        loader = DatasetLoader()
        mocker.patch.object(
            loader_module,
            "_load_embedding_generator",
            return_value=None,
        )
        mocker.patch.object(
            loader_module,
            "COCOInstanceSegmentationInput",
            return_value=instance_segmentation_input,
        )

        # Act
        dataset = loader.from_coco_instance_segmentations(data_json_path, image_folder_path)

        # We should not set the embeddingSearchEnabled
        assert lightly_studio_active_features == []
        assert dataset.name == Path(data_json_path).parent.name

        # Assert
        session = loader.session

        # Check if labels were created
        labels = session.exec(select(AnnotationLabelTable)).all()
        assert len(labels) == 2
        label_names = {lbl.annotation_label_name for lbl in labels}
        assert label_names == {"person", "car"}

        # Check if sample was created
        sample = session.exec(select(ImageTable)).first()
        assert sample is not None
        assert sample.file_name == "test_image.jpg"
        assert sample.width == 640
        assert sample.height == 480

        # Check for the annotations.
        annotations = session.exec(select(AnnotationBaseTable)).all()
        assert len(annotations) == 2

        polygon_annotation = annotations[0]
        assert polygon_annotation.annotation_label.annotation_label_name == "person"

        assert polygon_annotation.instance_segmentation_details is not None

        assert_contains_properties(
            polygon_annotation.instance_segmentation_details,
            {
                **test_polygon_bbox,
                "segmentation_mask": None,
            },
        )

        mask_annotation = annotations[1]
        assert mask_annotation.annotation_label.annotation_label_name == "car"

        assert mask_annotation.instance_segmentation_details is not None
        x, y, width, height = test_bounding_box.to_format(BoundingBoxFormat.XYWH)
        assert_contains_properties(
            mask_annotation.instance_segmentation_details,
            {
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "segmentation_mask": [1, 2, 1],
            },
        )
