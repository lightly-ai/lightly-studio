from typing import Iterable
from uuid import uuid4

from labelformat.model.binary_mask_segmentation import BinaryMaskSegmentation
from labelformat.model.bounding_box import BoundingBox, BoundingBoxFormat
from labelformat.model.category import Category
from labelformat.model.multipolygon import MultiPolygon
from sqlmodel import Session

from lightly_studio.core import labelformat_helpers
from lightly_studio.models.annotation.annotation_base import AnnotationType
from tests import helpers_resolvers


def test_get_segmentation_annotation_create__with_multipolygon() -> None:
    """Test creating segmentation annotation from MultiPolygon."""
    parent_sample_id = uuid4()
    annotation_label_id = uuid4()

    multipolygon = MultiPolygon(polygons=[[(10.0, 20.0), (30.0, 20.0), (30.0, 40.0), (10.0, 40.0)]])

    annotation = labelformat_helpers.get_segmentation_annotation_create(
        parent_sample_id=parent_sample_id,
        annotation_label_id=annotation_label_id,
        segmentation=multipolygon,
        annotation_type=AnnotationType.INSTANCE_SEGMENTATION,
    )

    assert annotation.parent_sample_id == parent_sample_id
    assert annotation.annotation_label_id == annotation_label_id
    assert annotation.annotation_type == AnnotationType.INSTANCE_SEGMENTATION
    assert annotation.x == 10
    assert annotation.y == 20
    assert annotation.width == 20
    assert annotation.height == 20
    assert annotation.segmentation_mask is None  # MultiPolygon doesn't have RLE


def test_get_segmentation_annotation_create__with_binary_mask() -> None:
    """Test creating segmentation annotation from BinaryMaskSegmentation."""
    parent_sample_id = uuid4()
    annotation_label_id = uuid4()

    # Create a simple binary mask using RLE encoding
    # RLE format: [start, length, start, length, ...]
    # This represents a 2x2 mask in the top-left of a 4x4 image
    binary_mask = BinaryMaskSegmentation.from_rle(
        rle_row_wise=[0, 2, 2, 2, 10],
        width=4,
        height=4,
        bounding_box=BoundingBox(xmin=0, ymin=0, xmax=2, ymax=2),
    )

    annotation = labelformat_helpers.get_segmentation_annotation_create(
        parent_sample_id=parent_sample_id,
        annotation_label_id=annotation_label_id,
        segmentation=binary_mask,
        annotation_type=AnnotationType.SEMANTIC_SEGMENTATION,
    )

    assert annotation.parent_sample_id == parent_sample_id
    assert annotation.annotation_label_id == annotation_label_id
    assert annotation.annotation_type == AnnotationType.SEMANTIC_SEGMENTATION
    assert annotation.x == 0
    assert annotation.y == 0
    assert annotation.width == 2
    assert annotation.height == 2
    assert annotation.segmentation_mask == [0, 2, 2, 2, 10]
    assert isinstance(annotation.segmentation_mask, list)


def test_get_object_detection_annotation_create() -> None:
    """Test creating object detection annotation from BoundingBox."""
    parent_sample_id = uuid4()
    annotation_label_id = uuid4()

    # Create a bounding box in XYXY format
    box = BoundingBox.from_format([10.5, 20.5, 30.5, 40.5], BoundingBoxFormat.XYXY)

    annotation = labelformat_helpers.get_object_detection_annotation_create(
        parent_sample_id=parent_sample_id,
        annotation_label_id=annotation_label_id,
        box=box,
        confidence=None,
    )

    # Verify annotation properties
    assert annotation.parent_sample_id == parent_sample_id
    assert annotation.annotation_label_id == annotation_label_id
    assert annotation.annotation_type == AnnotationType.OBJECT_DETECTION
    assert annotation.x == 10  # Converted to int and XYWH format
    assert annotation.y == 20
    assert annotation.width == 20
    assert annotation.height == 20
    assert annotation.confidence is None


def test_get_object_detection_annotation_create__with_confidence() -> None:
    """Test creating object detection annotation with confidence score."""
    parent_sample_id = uuid4()
    annotation_label_id = uuid4()

    # Create a bounding box in XYWH format
    box = BoundingBox.from_format([15.0, 25.0, 50.0, 75.0], BoundingBoxFormat.XYWH)
    confidence = 0.95

    annotation = labelformat_helpers.get_object_detection_annotation_create(
        parent_sample_id=parent_sample_id,
        annotation_label_id=annotation_label_id,
        box=box,
        confidence=confidence,
    )

    # Verify annotation properties
    assert annotation.parent_sample_id == parent_sample_id
    assert annotation.annotation_label_id == annotation_label_id
    assert annotation.annotation_type == AnnotationType.OBJECT_DETECTION
    assert annotation.x == 15
    assert annotation.y == 25
    assert annotation.width == 50
    assert annotation.height == 75
    assert annotation.confidence == 0.95


def test_create_label_map(db_session: Session) -> None:
    # Test the creation of new labels and re-use of existing labels
    collection_id = helpers_resolvers.create_collection(session=db_session).collection_id

    class TestLabels1:
        def get_categories(self) -> Iterable[Category]:
            return [
                Category(id=0, name="dog"),
                Category(id=1, name="cat"),
            ]

    label_input = TestLabels1()

    label_map_1 = labelformat_helpers.create_label_map(
        session=db_session,
        dataset_id=collection_id,
        input_labels=label_input,
    )

    class TestLabels2:
        def get_categories(self) -> Iterable[Category]:
            return [
                Category(id=0, name="dog"),
                Category(id=1, name="cat"),
                Category(id=2, name="bird"),
            ]

    label_input_2 = TestLabels2()

    label_map_2 = labelformat_helpers.create_label_map(
        session=db_session,
        dataset_id=collection_id,
        input_labels=label_input_2,
    )

    assert len(label_map_1) == 2  # dog and cat
    assert len(label_map_2) == 3  # dog, cat and bird

    # Compare label IDs for:
    assert label_map_2[0] == label_map_1[0]  # dog exists already
    assert label_map_2[1] == label_map_1[1]  # cat exists already
    assert label_map_2[2] not in label_map_1.values()  # bird is new
