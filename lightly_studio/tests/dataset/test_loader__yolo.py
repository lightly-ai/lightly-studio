from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pytest
from labelformat.formats.yolov8 import YOLOv8ObjectDetectionInput
from labelformat.model.bounding_box import BoundingBox, BoundingBoxFormat
from labelformat.model.category import Category
from labelformat.model.image import Image
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


@pytest.fixture
def test_bounding_box() -> BoundingBox:
    return BoundingBox(5, 10, 20, 30)


class MockYOLOv8ObjectDetectionInput(YOLOv8ObjectDetectionInput):
    """Mock class for a labelformat.formats.yolov8."""

    def __init__(self, bounding_box: BoundingBox) -> None:
        self.categories = [Category(0, "person"), Category(1, "car")]
        self.bounding_box = bounding_box

    def get_labels(self) -> Iterable[ImageObjectDetection]:
        image = Image(id=0, filename="test_image.jpg", width=640, height=480)
        objects = [SingleObjectDetection(self.categories[0], self.bounding_box)]
        return [ImageObjectDetection(image, objects)]

    def _images_dir(self) -> Path:
        return Path("/fake/path")

    def get_categories(self) -> list[Category]:
        return self.categories


@pytest.fixture
def mock_yolo_v8_data(test_bounding_box: BoundingBox) -> MockYOLOv8ObjectDetectionInput:
    return MockYOLOv8ObjectDetectionInput(test_bounding_box)


class TestDatasetLoader:
    def test_from_yolo(
        self,
        patch_loader: None,  # noqa: ARG002
        mocker: MockerFixture,
        mock_yolo_v8_data: YOLOv8ObjectDetectionInput,
        test_bounding_box: BoundingBox,
    ) -> None:
        # Clear the lightly_studio_active_features before the test
        lightly_studio_active_features.clear()

        # Arrange
        data_yaml_path = "/fake/path/data.yaml"
        loader = DatasetLoader()

        # Patch the YOLOv8ObjectDetectionInput.
        mocker.patch.object(
            loader_module,
            "YOLOv8ObjectDetectionInput",
            return_value=mock_yolo_v8_data,
        )

        # Act
        dataset = loader.from_yolo(data_yaml_path)
        assert dataset.name == Path(data_yaml_path).parent.name

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

        # check if sampleEmbedding was created
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

    def test_from_yolo__without_embedding_generator(
        self,
        patch_loader: None,  # noqa: ARG002
        mocker: MockerFixture,
        mock_yolo_v8_data: YOLOv8ObjectDetectionInput,
        test_bounding_box: BoundingBox,
    ) -> None:
        # Clear the lightly_studio_active_features before the test
        lightly_studio_active_features.clear()

        # Arrange
        data_yaml_path = "/fake/path/data.yaml"
        loader = DatasetLoader()

        # Patch EmbeddingGenerator.
        mocker.patch.object(
            loader_module,
            "_load_embedding_generator",
            return_value=None,
        )

        # Patch the YOLOv8ObjectDetectionInput.
        mocker.patch.object(
            loader_module,
            "YOLOv8ObjectDetectionInput",
            return_value=mock_yolo_v8_data,
        )

        # Act
        dataset = loader.from_yolo(data_yaml_path)
        assert dataset.name == Path(data_yaml_path).parent.name

        # We should not set the embeddingSearchEnabled
        # if embedding_generator is not provided
        assert lightly_studio_active_features == []

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

        # check if sampleEmbedding was created
        assert sample.embeddings is not None
        embedding_model = session.exec(select(EmbeddingModelTable)).first()
        assert embedding_model is None

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
