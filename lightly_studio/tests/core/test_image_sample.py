import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.core.annotation import (
    ClassificationCreate,
    InstanceSegmentationCreate,
    ObjectDetectionCreate,
    SemanticSegmentationCreate,
)
from lightly_studio.core.annotation.classification import ClassificationAnnotation
from lightly_studio.core.annotation.instance_segmentation import InstanceSegmentationAnnotation
from lightly_studio.core.annotation.object_detection import ObjectDetectionAnnotation
from lightly_studio.core.annotation.semantic_segmentation import SemanticSegmentationAnnotation
from lightly_studio.core.image_sample import ImageSample
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.resolvers import image_resolver
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
    create_tag,
)


class TestImageSample:
    def test_basic_fields_get(self, test_db: Session) -> None:
        collection = create_collection(session=test_db)
        image_table = create_image(
            session=test_db,
            collection_id=collection.collection_id,
            file_path_abs="/path/to/sample1.png",
            width=640,
            height=480,
        )
        sample = ImageSample(inner=image_table)

        # Test "get".
        assert sample.file_name == "sample1.png"
        assert sample.width == 640
        assert sample.height == 480
        assert sample.dataset_id == collection.collection_id
        assert sample.file_path_abs == "/path/to/sample1.png"
        assert sample.sample_id == image_table.sample_id
        assert sample.created_at == image_table.created_at
        assert sample.updated_at == image_table.updated_at

    def test_basic_fields_set(self, mocker: MockerFixture, test_db: Session) -> None:
        collection = create_collection(session=test_db)
        image_table = create_image(
            session=test_db,
            collection_id=collection.collection_id,
        )
        sample = ImageSample(inner=image_table)

        # Spy on commit.
        spy_commit = mocker.spy(test_db, "commit")

        # Test "set".
        sample.file_name = "sample1.png"
        assert spy_commit.call_count == 1
        sample.width = 1000
        assert spy_commit.call_count == 2

        new_image_table = image_resolver.get_by_id(session=test_db, sample_id=sample.sample_id)
        assert new_image_table is not None
        assert new_image_table.file_name == "sample1.png"
        assert new_image_table.width == 1000

    def test_add_tag(self, test_db: Session) -> None:
        collection = create_collection(session=test_db)
        image_table = create_image(
            session=test_db,
            collection_id=collection.collection_id,
        )
        sample = ImageSample(inner=image_table)

        # Test adding a tag.
        assert [tag.name for tag in sample.sample_table.tags] == []
        sample.add_tag("tag1")
        assert [tag.name for tag in sample.sample_table.tags] == ["tag1"]
        sample.add_tag("tag2")
        assert sorted([tag.name for tag in sample.sample_table.tags]) == ["tag1", "tag2"]
        sample.add_tag("tag1")
        assert sorted([tag.name for tag in sample.sample_table.tags]) == ["tag1", "tag2"]

    def test_remove_tag(self, test_db: Session) -> None:
        collection = create_collection(session=test_db)
        image_table = create_image(
            session=test_db,
            collection_id=collection.collection_id,
        )
        sample = ImageSample(inner=image_table)

        # Add some tags first
        sample.add_tag("tag1")
        sample.add_tag("tag2")
        assert sorted([tag.name for tag in sample.sample_table.tags]) == ["tag1", "tag2"]

        # Test removing an existing, associated tag
        sample.remove_tag("tag1")
        assert [tag.name for tag in sample.sample_table.tags] == ["tag2"]

        # Test removing a non-existent tag (should not error)
        sample.remove_tag("nonexistent")
        assert [tag.name for tag in sample.sample_table.tags] == ["tag2"]

        # Test removing a tag that exists in database but isn't associated with sample
        create_tag(session=test_db, collection_id=collection.collection_id, tag_name="unassociated")
        sample.remove_tag("unassociated")
        assert [tag.name for tag in sample.sample_table.tags] == ["tag2"]

        # Remove the last tag
        sample.remove_tag("tag2")
        assert [tag.name for tag in sample.sample_table.tags] == []

    def test_tags_property_get(self, test_db: Session) -> None:
        collection = create_collection(session=test_db)
        image_table = create_image(
            session=test_db,
            collection_id=collection.collection_id,
        )
        sample = ImageSample(inner=image_table)

        # Test empty tags
        assert sample.tags == set()

        # Test with tags
        sample.add_tag("tag1")
        sample.add_tag("tag2")
        assert sample.tags == {"tag1", "tag2"}

    def test_tags_property_set(self, test_db: Session) -> None:
        collection = create_collection(session=test_db)
        image_table = create_image(
            session=test_db,
            collection_id=collection.collection_id,
        )
        sample = ImageSample(inner=image_table)

        # Test setting tags from empty to multiple
        sample.tags = {"tag1", "tag2", "tag3"}
        assert sample.tags == {"tag1", "tag2", "tag3"}
        assert sorted([tag.name for tag in sample.sample_table.tags]) == ["tag1", "tag2", "tag3"]

        # Test replacing existing tags with new ones
        sample.tags = {"tag2", "tag4", "tag5"}
        assert sample.tags == {"tag2", "tag4", "tag5"}
        assert sorted([tag.name for tag in sample.sample_table.tags]) == ["tag2", "tag4", "tag5"]

        # Test clearing all tags
        sample.tags = set()
        assert sample.tags == set()
        assert [tag.name for tag in sample.sample_table.tags] == []

    def test_metadata(self, test_db: Session) -> None:
        collection = create_collection(session=test_db)
        image_table = create_image(
            session=test_db,
            collection_id=collection.collection_id,
        )
        sample = ImageSample(inner=image_table)

        # Test getting from empty metadata
        assert sample.metadata["nonexistent"] is None

        # Test setting metadata on a sample with no existing metadata
        sample.metadata["string_key"] = "string_value"
        sample.metadata["int_key"] = 123
        sample.metadata["float_key"] = 45.67
        sample.metadata["bool_key"] = True
        sample.metadata["list_key"] = [1, 2, 3]
        sample.metadata["dict_key"] = {"nested": "value"}

        # Verify all values were set correctly
        assert sample.metadata["string_key"] == "string_value"
        assert sample.metadata["int_key"] == 123
        assert sample.metadata["float_key"] == 45.67
        assert sample.metadata["bool_key"] is True
        assert sample.metadata["list_key"] == [1, 2, 3]
        assert sample.metadata["dict_key"] == {"nested": "value"}

        # Test overwriting existing metadata values
        sample.metadata["string_key"] = "updated_value"
        assert sample.metadata["string_key"] == "updated_value"

    def test_metadata__schema_must_match(self, test_db: Session) -> None:
        collection = create_collection(session=test_db)
        image_table1 = create_image(
            session=test_db,
            collection_id=collection.collection_id,
            file_path_abs="/path/to/sample1.png",
        )
        image_table2 = create_image(
            session=test_db,
            collection_id=collection.collection_id,
            file_path_abs="/path/to/sample2.png",
        )
        sample1 = ImageSample(inner=image_table1)
        sample2 = ImageSample(inner=image_table2)

        # Set the initial value to a string
        sample1.metadata["key"] = "string_value"

        # Test setting the value to a different type fails
        with pytest.raises(ValueError, match="Expected string, got integer"):
            sample1.metadata["key"] = 123

        # For a different sample, the same schema check does not apply
        # TODO(Michal, 9/2025): But shouldn't it?
        sample2.metadata["key"] = 123

    def test_add_caption(self, test_db: Session) -> None:
        collection = create_collection(session=test_db)
        image_table = create_image(
            session=test_db,
            collection_id=collection.collection_id,
        )
        sample = ImageSample(inner=image_table)

        # Test adding a caption.
        sample.add_caption("caption3")
        assert sample.captions == ["caption3"]
        sample.add_caption("caption2")
        assert sample.captions == ["caption3", "caption2"]
        sample.add_caption("caption1")
        assert sample.captions == ["caption3", "caption2", "caption1"]

    def test_captions_setter(self, test_db: Session) -> None:
        collection = create_collection(session=test_db)
        image_table = create_image(
            session=test_db,
            collection_id=collection.collection_id,
        )
        sample = ImageSample(inner=image_table)

        sample.captions = ["caption1", "caption2"]
        assert sorted(sample.captions) == ["caption1", "caption2"]

        sample.captions = ["caption3"]
        assert sample.captions == ["caption3"]

    def test_annotations_object_detection(
        self,
        test_db: Session,
    ) -> None:
        collection = create_collection(session=test_db)
        image_table = create_image(
            session=test_db,
            collection_id=collection.collection_id,
        )
        zebra_label = create_annotation_label(
            session=test_db,
            dataset_id=collection.collection_id,
            label_name="zebra",
        )
        image = ImageSample(inner=image_table)
        create_annotation(
            session=test_db,
            collection_id=collection.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=zebra_label.annotation_label_id,
            annotation_data={"x": 47, "y": 64, "width": 400, "height": 300, "confidence": 0.7},
        )

        annotations = image.annotations
        assert len(annotations) == 1
        assert isinstance(annotations[0], ObjectDetectionAnnotation)
        assert annotations[0].label == "zebra"
        assert annotations[0].confidence == pytest.approx(0.7)
        assert annotations[0].x == 47
        assert annotations[0].y == 64
        assert annotations[0].width == 400
        assert annotations[0].height == 300

    def test_annotations_instance_segmentation(
        self,
        test_db: Session,
    ) -> None:
        collection = create_collection(session=test_db)
        image_table = create_image(
            session=test_db,
            collection_id=collection.collection_id,
        )
        cat_label = create_annotation_label(
            session=test_db,
            dataset_id=collection.collection_id,
            label_name="cat",
        )
        image = ImageSample(inner=image_table)
        create_annotation(
            session=test_db,
            collection_id=collection.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=cat_label.annotation_label_id,
            annotation_type=AnnotationType.INSTANCE_SEGMENTATION,
            annotation_data={
                "x": 10,
                "y": 20,
                "width": 100,
                "height": 200,
                "confidence": 0.9,
                "segmentation_mask": [1, 2, 3],
            },
        )

        annotations = image.annotations
        assert len(annotations) == 1
        assert isinstance(annotations[0], InstanceSegmentationAnnotation)
        assert annotations[0].label == "cat"
        assert annotations[0].confidence == pytest.approx(0.9)
        assert annotations[0].x == 10
        assert annotations[0].y == 20
        assert annotations[0].width == 100
        assert annotations[0].height == 200
        assert annotations[0].segmentation_mask == [1, 2, 3]

    def test_annotations_classification(
        self,
        test_db: Session,
    ) -> None:
        collection = create_collection(session=test_db)
        image_table = create_image(
            session=test_db,
            collection_id=collection.collection_id,
        )
        cat_label = create_annotation_label(
            session=test_db,
            dataset_id=collection.collection_id,
            label_name="cat",
        )
        image = ImageSample(inner=image_table)
        create_annotation(
            session=test_db,
            collection_id=collection.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=cat_label.annotation_label_id,
            annotation_type=AnnotationType.CLASSIFICATION,
            annotation_data={"confidence": 0.8},
        )

        annotations = image.annotations
        assert len(annotations) == 1
        assert isinstance(annotations[0], ClassificationAnnotation)
        assert annotations[0].label == "cat"
        assert annotations[0].confidence == pytest.approx(0.8)

    def test_annotations_multiple_types(
        self,
        test_db: Session,
    ) -> None:
        collection = create_collection(session=test_db)
        image_table = create_image(
            session=test_db,
            collection_id=collection.collection_id,
        )
        cat_label = create_annotation_label(
            session=test_db,
            dataset_id=collection.collection_id,
            label_name="cat",
        )
        image = ImageSample(inner=image_table)
        create_annotation(
            session=test_db,
            collection_id=collection.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=cat_label.annotation_label_id,
            annotation_data={"x": 47, "y": 64, "width": 100, "height": 200},
        )
        create_annotation(
            session=test_db,
            collection_id=collection.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=cat_label.annotation_label_id,
            annotation_type=AnnotationType.INSTANCE_SEGMENTATION,
            annotation_data={
                "x": 10,
                "y": 20,
                "width": 100,
                "height": 200,
                "segmentation_mask": [1, 2, 3],
            },
        )
        create_annotation(
            session=test_db,
            collection_id=collection.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=cat_label.annotation_label_id,
            annotation_type=AnnotationType.CLASSIFICATION,
        )

        annotations = image.annotations
        assert len(annotations) == 3
        assert isinstance(annotations[0], ObjectDetectionAnnotation)
        assert isinstance(annotations[1], InstanceSegmentationAnnotation)
        assert isinstance(annotations[2], ClassificationAnnotation)

    def test_annotations_semantic_segmentation(
        self,
        test_db: Session,
    ) -> None:
        collection = create_collection(session=test_db)
        image_table = create_image(
            session=test_db,
            collection_id=collection.collection_id,
        )
        road_label = create_annotation_label(
            session=test_db,
            dataset_id=collection.collection_id,
            label_name="road",
        )
        image = ImageSample(inner=image_table)
        create_annotation(
            session=test_db,
            collection_id=collection.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=road_label.annotation_label_id,
            annotation_type=AnnotationType.SEMANTIC_SEGMENTATION,
            annotation_data={
                "confidence": 0.8,
                "segmentation_mask": [0, 0, 1, 1, 0, 0],
            },
        )

        annotations = image.annotations
        assert len(annotations) == 1
        assert isinstance(annotations[0], SemanticSegmentationAnnotation)
        assert annotations[0].label == "road"
        assert annotations[0].confidence == pytest.approx(0.8)
        assert annotations[0].segmentation_mask == [0, 0, 1, 1, 0, 0]

    def test_add_annotation_classification(
        self,
        test_db: Session,
    ) -> None:
        collection = create_collection(session=test_db)
        image_table = create_image(
            session=test_db,
            collection_id=collection.collection_id,
        )
        cat_label = create_annotation_label(
            session=test_db,
            dataset_id=collection.collection_id,
            label_name="cat",
        )
        image = ImageSample(inner=image_table)

        # Add classification annotation.
        annotation_create = ClassificationCreate(
            annotation_label_id=cat_label.annotation_label_id,
            confidence=0.75,
        )
        image.add_annotation(annotation_create)

        # Verify annotation was added.
        annotations = image.annotations
        assert len(annotations) == 1
        assert isinstance(annotations[0], ClassificationAnnotation)
        assert annotations[0].label == "cat"
        assert annotations[0].confidence == pytest.approx(0.75)

    def test_add_annotation_object_detection(
        self,
        test_db: Session,
    ) -> None:
        collection = create_collection(session=test_db)
        image_table = create_image(
            session=test_db,
            collection_id=collection.collection_id,
        )
        dog_label = create_annotation_label(
            session=test_db,
            dataset_id=collection.collection_id,
            label_name="dog",
        )
        image = ImageSample(inner=image_table)

        # Add object detection annotation.
        annotation_create = ObjectDetectionCreate(
            annotation_label_id=dog_label.annotation_label_id,
            confidence=0.9,
            x=10,
            y=20,
            width=30,
            height=40,
        )
        image.add_annotation(annotation_create)

        # Verify annotation was added.
        annotations = image.annotations
        assert len(annotations) == 1
        assert isinstance(annotations[0], ObjectDetectionAnnotation)
        assert annotations[0].label == "dog"
        assert annotations[0].confidence == pytest.approx(0.9)
        assert annotations[0].x == 10
        assert annotations[0].y == 20
        assert annotations[0].width == 30
        assert annotations[0].height == 40

    def test_add_annotation_instance_segmentation(
        self,
        test_db: Session,
    ) -> None:
        collection = create_collection(session=test_db)
        image_table = create_image(
            session=test_db,
            collection_id=collection.collection_id,
        )
        cat_label = create_annotation_label(
            session=test_db,
            dataset_id=collection.collection_id,
            label_name="cat",
        )
        image = ImageSample(inner=image_table)

        # Add instance segmentation annotation.
        annotation_create = InstanceSegmentationCreate(
            annotation_label_id=cat_label.annotation_label_id,
            confidence=0.95,
            x=5,
            y=15,
            width=25,
            height=35,
            segmentation_mask=[1, 2, 3, 4, 5],
        )
        image.add_annotation(annotation_create)

        # Verify annotation was added.
        annotations = image.annotations
        assert len(annotations) == 1
        assert isinstance(annotations[0], InstanceSegmentationAnnotation)
        assert annotations[0].label == "cat"
        assert annotations[0].confidence == pytest.approx(0.95)
        assert annotations[0].x == 5
        assert annotations[0].y == 15
        assert annotations[0].width == 25
        assert annotations[0].height == 35
        assert annotations[0].segmentation_mask == [1, 2, 3, 4, 5]

    def test_add_annotation_semantic_segmentation(
        self,
        test_db: Session,
    ) -> None:
        collection = create_collection(session=test_db)
        image_table = create_image(
            session=test_db,
            collection_id=collection.collection_id,
        )
        road_label = create_annotation_label(
            session=test_db,
            dataset_id=collection.collection_id,
            label_name="road",
        )
        image = ImageSample(inner=image_table)

        # Add semantic segmentation annotation.
        annotation_create = SemanticSegmentationCreate(
            annotation_label_id=road_label.annotation_label_id,
            confidence=0.85,
            x=0,
            y=0,
            width=100,
            height=100,
            segmentation_mask=[0, 0, 1, 1, 0, 0],
        )
        image.add_annotation(annotation_create)

        # Verify annotation was added.
        annotations = image.annotations
        assert len(annotations) == 1
        assert isinstance(annotations[0], SemanticSegmentationAnnotation)
        assert annotations[0].label == "road"
        assert annotations[0].confidence == pytest.approx(0.85)
        assert annotations[0].x == 0
        assert annotations[0].y == 0
        assert annotations[0].width == 100
        assert annotations[0].height == 100
        assert annotations[0].segmentation_mask == [0, 0, 1, 1, 0, 0]
