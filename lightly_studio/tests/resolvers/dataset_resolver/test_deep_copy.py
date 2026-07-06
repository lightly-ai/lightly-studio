"""Tests for deep_copy resolver."""

import uuid

import pytest
from sqlmodel import Session

from lightly_studio.metadata.gps_coordinate import GPSCoordinate
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationTable
from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.models.annotation.segmentation import SegmentationAnnotationTable
from lightly_studio.models.collection import SampleType
from lightly_studio.models.evaluation_annotation_metric import EvaluationAnnotationMetricCreate
from lightly_studio.models.evaluation_run import EvaluationRunCreate, EvaluationTaskType
from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricCreate
from lightly_studio.models.image import ImageCreate
from lightly_studio.resolvers import (
    annotation_resolver,
    collection_resolver,
    dataset_resolver,
    embedding_model_resolver,
    evaluation_annotation_metric_resolver,
    evaluation_run_resolver,
    evaluation_sample_metric_resolver,
    image_resolver,
    metadata_resolver,
    object_track_resolver,
    sample_embedding_resolver,
    sample_resolver,
)
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_embedding_model,
    create_image,
    create_sample_embedding,
)
from tests.resolvers.evaluation_sample_metric_resolver import (
    helpers as evaluation_sample_metric_helpers,
)
from tests.resolvers.evaluation_sample_metric_resolver.helpers import (
    TruePositiveMetricStub,
    create_annotation_metrics,
)

# Deep copying is enterprise-only and PostgreSQL-backed; skip on the default DuckDB run.
pytestmark = pytest.mark.postgres_only


def test_deep_copy__empty_collection(db_session: Session) -> None:
    # Arrange
    original = create_collection(session=db_session, collection_name="original")

    # Act
    copied = dataset_resolver.deep_copy(
        session=db_session,
        dataset_id=original.dataset_id,
        copy_name="copied",
    )

    # Assert - new collection created with different ID
    assert copied.collection_id != original.collection_id
    assert copied.name == "copied"
    assert copied.sample_type == original.sample_type
    assert copied.parent_collection_id is None


def test_deep_copy__with_images(db_session: Session) -> None:
    # Arrange
    original = create_collection(session=db_session, collection_name="original")
    img1 = create_image(
        session=db_session, collection_id=original.collection_id, file_path_abs="/a.png"
    )
    img2 = create_image(
        session=db_session, collection_id=original.collection_id, file_path_abs="/b.png"
    )

    # Act
    copied = dataset_resolver.deep_copy(
        session=db_session,
        dataset_id=original.dataset_id,
        copy_name="copied",
    )
    # Add another image to the original collection after copying
    create_image(session=db_session, collection_id=original.collection_id, file_path_abs="/c.png")

    # Assert - new collection has new samples
    copied_samples_result = sample_resolver.get_filtered_samples(
        session=db_session,
        collection_id=copied.collection_id,
    )
    assert copied_samples_result.total_count == 2

    # Assert - sample IDs are different
    original_ids = {img1.sample_id, img2.sample_id}
    copied_ids = {s.sample_id for s in copied_samples_result.samples}
    assert original_ids.isdisjoint(copied_ids)

    # Assert - image data preserved
    copied_images = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=copied.collection_id,
    )
    copied_paths = {s.file_path_abs for s in copied_images.samples}
    assert copied_paths == {"/a.png", "/b.png"}

    # Assert - original collection has 3 samples
    original_samples_result = sample_resolver.get_filtered_samples(
        session=db_session,
        collection_id=original.collection_id,
    )
    assert original_samples_result.total_count == 3

    # Assert - copied collection remains with 2 samples
    copied_samples_result_after = sample_resolver.get_filtered_samples(
        session=db_session,
        collection_id=copied.collection_id,
    )
    assert copied_samples_result_after.total_count == 2


def test_deep_copy__with_hierarchy(db_session: Session) -> None:
    # Arrange
    root = create_collection(
        session=db_session, collection_name="original_dataset", sample_type=SampleType.VIDEO
    )
    child = create_collection(
        session=db_session,
        collection_name="original_dataset__video_frame",
        parent_collection_id=root.collection_id,
        sample_type=SampleType.VIDEO_FRAME,
    )

    # Act
    copied_root = dataset_resolver.deep_copy(
        session=db_session,
        dataset_id=root.dataset_id,
        copy_name="copied_dataset",
    )

    # Assert - hierarchy copied
    hierarchy = dataset_resolver.get_hierarchy(
        session=db_session, dataset_id=copied_root.dataset_id
    )
    assert len(hierarchy) == 2

    # Assert - child name derived correctly
    assert hierarchy[0].name == "copied_dataset"
    assert hierarchy[1].name == "copied_dataset__video_frame"

    # Assert - child points to new parent
    copied_child = hierarchy[1]
    assert copied_child.parent_collection_id == copied_root.collection_id
    assert copied_child.collection_id != child.collection_id

    # Assert - original hierarchy unchanged
    original_hierarchy = dataset_resolver.get_hierarchy(
        session=db_session, dataset_id=root.dataset_id
    )
    assert len(original_hierarchy) == 2
    assert original_hierarchy[1].parent_collection_id == root.collection_id


def test_deep_copy__with_metadata(db_session: Session) -> None:
    # Arrange
    original = create_collection(session=db_session, collection_name="original")
    img = create_image(
        session=db_session, collection_id=original.collection_id, file_path_abs="/test.png"
    )

    img.sample["temperature"] = 25
    img.sample["location"] = "city"
    img.sample["gps_location"] = GPSCoordinate(lat=40.7128, lon=-74.0060)

    # Act
    copied = dataset_resolver.deep_copy(
        session=db_session,
        dataset_id=original.dataset_id,
        copy_name="copied",
    )

    # Assert - metadata gets copied
    copied_samples = sample_resolver.get_filtered_samples(
        session=db_session,
        collection_id=copied.collection_id,
    )
    assert copied_samples.total_count == 1
    copied_sample = copied_samples.samples[0]

    copied_metadata = metadata_resolver.get_by_sample_id(
        session=db_session,
        sample_id=copied_sample.sample_id,
    )
    assert copied_metadata is not None

    # Assert - data preserved
    assert copied_metadata.data["temperature"] == 25
    assert copied_metadata.data["location"] == "city"
    assert copied_metadata.data["gps_location"]["lat"] == 40.7128
    assert copied_metadata.data["gps_location"]["lon"] == -74.0060

    assert copied_metadata.metadata_schema["gps_location"] == "gps_coordinate"
    assert copied_metadata.metadata_schema["location"] == "string"
    assert copied_metadata.metadata_schema["temperature"] == "integer"

    # Assert - modifications to copied metadata do not affect original
    copied_sample["temperature"] = 30
    original_metadata = metadata_resolver.get_by_sample_id(
        session=db_session, sample_id=img.sample.sample_id
    )
    assert original_metadata is not None
    assert original_metadata.data["temperature"] == 25
    assert copied_metadata.data["temperature"] == 30


def test_deep_copy__with_nested_metadata(db_session: Session) -> None:
    """Verify nested metadata structures are properly deep copied.

    This test ensures that modifying nested dicts/lists in copied metadata
    does not affect the original metadata (i.e., model_dump() properly
    deep copies JSON fields).
    """
    # Arrange
    original = create_collection(session=db_session, collection_name="original")
    img = create_image(
        session=db_session, collection_id=original.collection_id, file_path_abs="/test.png"
    )

    # Set metadata with nested structures
    img.sample["config"] = {"threshold": 0.5, "options": {"enabled": True, "mode": "auto"}}
    img.sample["some_list"] = ["el1", "el2"]

    # Act
    copied = dataset_resolver.deep_copy(
        session=db_session,
        dataset_id=original.dataset_id,
        copy_name="copied",
    )

    # Get copied metadata
    copied_samples = sample_resolver.get_filtered_samples(
        session=db_session,
        collection_id=copied.collection_id,
    )
    copied_sample = copied_samples.samples[0]
    copied_metadata = metadata_resolver.get_by_sample_id(
        session=db_session, sample_id=copied_sample.sample_id
    )
    assert copied_metadata is not None

    # Assert - nested data was copied correctly
    assert copied_metadata.data["config"]["threshold"] == 0.5
    assert copied_metadata.data["config"]["options"]["enabled"] is True
    assert copied_metadata.data["config"]["options"]["mode"] == "auto"
    assert copied_metadata.data["some_list"] == ["el1", "el2"]

    # Act - modify nested values in the copy
    copied_metadata.data["config"]["threshold"] = 0.9
    copied_metadata.data["config"]["options"]["enabled"] = False
    copied_metadata.data["config"]["options"]["mode"] = "manual"
    copied_metadata.data["some_list"].append("el3")

    # Assert - original metadata is unchanged
    original_metadata = metadata_resolver.get_by_sample_id(
        session=db_session, sample_id=img.sample.sample_id
    )
    assert original_metadata is not None
    assert original_metadata.data["config"]["threshold"] == 0.5
    assert original_metadata.data["config"]["options"]["enabled"] is True
    assert copied_metadata.data["config"]["options"]["mode"] == "manual"
    assert original_metadata.data["some_list"] == ["el1", "el2"]


def test_deep_copy__with_embeddings(db_session: Session) -> None:
    # Arrange
    original = create_collection(session=db_session, collection_name="original")
    img1 = create_image(
        session=db_session, collection_id=original.collection_id, file_path_abs="/a.png"
    )
    img2 = create_image(
        session=db_session, collection_id=original.collection_id, file_path_abs="/b.png"
    )

    # Create embedding model
    embedding_model = create_embedding_model(
        session=db_session,
        collection_id=original.collection_id,
        embedding_model_name="test_model",
        embedding_dimension=512,
    )

    # Create embeddings
    create_sample_embedding(
        session=db_session,
        sample_id=img1.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[1.0, 2.0, 3.0],
    )
    create_sample_embedding(
        session=db_session,
        sample_id=img2.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[4.0, 5.0, 6.0],
    )

    # Act
    copied = dataset_resolver.deep_copy(
        session=db_session,
        dataset_id=original.dataset_id,
        copy_name="copied",
    )

    # Assert - embedding model is copied with new ID
    copied_embedding_models = embedding_model_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=copied.collection_id,
    )
    assert len(copied_embedding_models) == 1
    copied_model = copied_embedding_models[0]
    assert copied_model.embedding_model_id != embedding_model.embedding_model_id
    assert copied_model.name == embedding_model.name
    assert copied_model.embedding_model_hash == embedding_model.embedding_model_hash
    assert copied_model.embedding_dimension == embedding_model.embedding_dimension

    # Assert - embeddings copied
    copied_samples = sample_resolver.get_filtered_samples(
        session=db_session,
        collection_id=copied.collection_id,
    )
    assert copied_samples.total_count == 2

    # Assert - copied embeddings can be loaded by the copied_model.embedding_model_id
    copied_embeddings = sample_embedding_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=copied.collection_id,
        embedding_model_id=copied_model.embedding_model_id,
    )
    assert len(copied_embeddings) == 2

    # Assert - embedding vectors are preserved
    copied_vectors = {tuple(emb.embedding) for emb in copied_embeddings}
    assert (1.0, 2.0, 3.0) in copied_vectors
    assert (4.0, 5.0, 6.0) in copied_vectors

    # Assert - sample IDs are different
    original_sample_ids = {img1.sample_id, img2.sample_id}
    copied_sample_ids = {emb.sample_id for emb in copied_embeddings}
    assert original_sample_ids.isdisjoint(copied_sample_ids)


def test_deep_copy__can_delete_original_after_copy(db_session: Session) -> None:
    """Verify deleting original collection after deep copy doesn't cause FK errors."""
    # Arrange
    original = create_collection(session=db_session, collection_name="original")
    original_collection_id = original.collection_id
    img = create_image(
        session=db_session, collection_id=original.collection_id, file_path_abs="/a.png"
    )
    label = create_annotation_label(
        session=db_session, root_collection_id=original.collection_id, label_name="test"
    )

    create_annotations(
        session=db_session,
        collection_id=original.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=img.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
            ),
            AnnotationDetails(
                sample_id=img.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
                x=10,
                y=20,
                width=30,
                height=40,
            ),
            AnnotationDetails(
                sample_id=img.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.SEGMENTATION_MASK,
                x=2,
                y=4,
                width=6,
                height=8,
                segmentation_mask=[1, 0, 0, 1],
            ),
        ],
    )

    embedding_model = create_embedding_model(
        session=db_session,
        collection_id=original.collection_id,
        embedding_model_name="test",
        embedding_dimension=3,
    )
    create_sample_embedding(
        session=db_session,
        sample_id=img.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[1.0, 2.0, 3.0],
    )

    # Act - deep copy, then delete original
    copied = dataset_resolver.deep_copy(
        session=db_session,
        dataset_id=original.dataset_id,
        copy_name="copied",
    )
    dataset_resolver.delete_dataset(
        session=db_session,
        dataset_id=original.dataset_id,
    )

    # Assert - copied collection still exists with its data
    copied_check = collection_resolver.get_by_id(
        session=db_session, collection_id=copied.collection_id
    )
    assert copied_check is not None
    assert (
        collection_resolver.get_by_id(session=db_session, collection_id=original_collection_id)
        is None
    )

    # Assert - copied collection still has embeddings
    copied_embedding_models = embedding_model_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=copied.collection_id,
    )
    assert len(copied_embedding_models) == 1
    copied_embeddings = sample_embedding_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=copied.collection_id,
        embedding_model_id=copied_embedding_models[0].embedding_model_id,
    )
    assert len(copied_embeddings) == 1

    # Assert - copied collection still has annotations
    copied_annotations = annotation_resolver.get_all(
        session=db_session,
        filters=AnnotationsFilter(collection_ids=[copied.children[0].collection_id]),
    )
    assert copied_annotations.total_count == 3


def test_deep_copy__with_evaluation_sample_metrics(db_session: Session) -> None:
    # Arrange
    dataset = create_collection(session=db_session, collection_name="original")
    run = evaluation_sample_metric_helpers.create_run(
        session=db_session, collection_id=dataset.collection_id
    )
    image = create_image(session=db_session, collection_id=dataset.collection_id)
    evaluation_sample_metric_resolver.create_many(
        session=db_session,
        records=[
            EvaluationSampleMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                metric_name="precision",
                value=0.9,
            ),
            EvaluationSampleMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                metric_name="recall",
                value=0.7,
            ),
        ],
    )

    # Act
    copied = dataset_resolver.deep_copy(
        session=db_session,
        dataset_id=dataset.dataset_id,
        copy_name="copied",
    )

    # Assert - copied dataset has one evaluation run with the same metrics
    copied_runs = evaluation_run_resolver.get_all_by_dataset_id(
        session=db_session,
        dataset_id=copied.dataset_id,
    )
    assert len(copied_runs) == 1
    copied_run = copied_runs[0]
    assert copied_run.id != run.id

    copied_metrics = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=copied_run.id,
    )
    assert len(copied_metrics) == 2
    metric_map = {m.metric_name: m.value for m in copied_metrics}
    assert metric_map == pytest.approx({"precision": 0.9, "recall": 0.7})

    # Assert - copied metrics reference new sample IDs (not the originals)
    original_sample_ids = {image.sample_id}
    copied_sample_ids = {m.sample_id for m in copied_metrics}
    assert original_sample_ids.isdisjoint(copied_sample_ids)

    # Assert - original run metrics are untouched
    original_metrics = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=run.id,
    )
    assert len(original_metrics) == 2


def test_deep_copy__raises_for_nonexistent_dataset(db_session: Session) -> None:
    # Arrange
    nonexistent_id = uuid.uuid4()

    # Act & Assert
    with pytest.raises(ValueError, match="not found"):
        dataset_resolver.deep_copy(
            session=db_session,
            dataset_id=nonexistent_id,
            copy_name="test",
        )


def test_deep_copy__with_annotations(db_session: Session) -> None:
    # Arrange
    original = create_collection(session=db_session, collection_name="original")
    img = create_image(
        session=db_session, collection_id=original.collection_id, file_path_abs="/a.png"
    )
    label = create_annotation_label(
        session=db_session, root_collection_id=original.collection_id, label_name="test"
    )
    (original_track_id,) = object_track_resolver.create_many(
        session=db_session,
        tracks=[ObjectTrackCreate(object_track_number=7, dataset_id=original.dataset_id)],
    )

    classification, obj_detection, instance_seg = create_annotations(
        session=db_session,
        collection_id=original.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=img.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
            ),
            AnnotationDetails(
                sample_id=img.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
                x=10,
                y=20,
                width=30,
                height=40,
                object_track_id=original_track_id,
            ),
            AnnotationDetails(
                sample_id=img.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.SEGMENTATION_MASK,
                x=2,
                y=4,
                width=6,
                height=8,
                segmentation_mask=[1, 0, 0, 1],
            ),
        ],
    )

    original_sample_ids = {
        classification.sample_id,
        obj_detection.sample_id,
        instance_seg.sample_id,
    }

    # Act
    copied = dataset_resolver.deep_copy(
        session=db_session,
        dataset_id=original.dataset_id,
        copy_name="copied",
    )

    # Assert - 3 annotations exist in the copied collection
    result = annotation_resolver.get_all(
        session=db_session,
        filters=AnnotationsFilter(collection_ids=[copied.children[0].collection_id]),
    )
    assert result.total_count == 3

    # Assert - all annotation sample_ids differ from originals
    copied_sample_ids = {a.sample_id for a in result.annotations}
    assert original_sample_ids.isdisjoint(copied_sample_ids)

    # Build lookup by annotation type for copied annotations
    copied_by_type = {a.annotation_type: a for a in result.annotations}

    # Assert - classification annotation copied (no detail tables)
    copied_cls = copied_by_type[AnnotationType.CLASSIFICATION]
    assert copied_cls.annotation_type == AnnotationType.CLASSIFICATION
    assert copied_cls.object_detection_details is None
    assert copied_cls.segmentation_details is None

    # Assert - object detection detail table copied
    copied_od = copied_by_type[AnnotationType.OBJECT_DETECTION]
    od_detail = db_session.get(ObjectDetectionAnnotationTable, copied_od.sample_id)
    assert od_detail is not None
    assert od_detail.x == 10
    assert od_detail.y == 20
    assert od_detail.width == 30
    assert od_detail.height == 40
    assert copied_od.object_track_id is not None
    assert copied_od.object_track_id != original_track_id
    copied_track = object_track_resolver.get_by_id(
        session=db_session, object_track_id=copied_od.object_track_id
    )
    assert copied_track is not None
    assert copied_track.object_track_number == 7
    assert copied_track.dataset_id == copied.dataset_id

    # Assert - segmentation mask detail table copied
    copied_is = copied_by_type[AnnotationType.SEGMENTATION_MASK]
    is_detail = db_session.get(SegmentationAnnotationTable, copied_is.sample_id)
    assert is_detail is not None
    assert is_detail.x == 2
    assert is_detail.y == 4
    assert is_detail.width == 6
    assert is_detail.height == 8
    assert is_detail.segmentation_mask == [1, 0, 0, 1]


@pytest.mark.skip(reason="On an M4 Pro, it takes 47s for duckdb and 38s for postgres.")
def test_deep_copy__exceeds_postgres_param_limit(db_session: Session) -> None:
    # More samples than PostgreSQL's 65,535-parameter cap, so the in-memory id lists that
    # deep_copy feeds into its membership queries overflow an expanding IN clause.
    n_samples = 70_000
    original = create_collection(session=db_session, collection_name="original")
    sample_ids = image_resolver.create_many(
        session=db_session,
        collection_id=original.collection_id,
        samples=[
            ImageCreate(
                file_path_abs=f"/sample_{i}.png",
                file_name=f"sample_{i}.png",
                width=640,
                height=480,
            )
            for i in range(n_samples)
        ],
    )
    label = create_annotation_label(session=db_session, root_collection_id=original.collection_id)
    create_annotations(
        session=db_session,
        collection_id=original.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
            )
            for sample_id in sample_ids
        ],
    )

    # Act
    copied = dataset_resolver.deep_copy(
        session=db_session,
        dataset_id=original.dataset_id,
        copy_name="copied",
    )

    # Assert - copied collection is distinct and holds all images.
    assert copied.collection_id != original.collection_id
    copied_samples = sample_resolver.get_filtered_samples(
        session=db_session,
        collection_id=copied.collection_id,
    )
    assert copied_samples.total_count == n_samples

    # Assert - all annotations were copied into the new annotation child collection.
    copied_annotations = annotation_resolver.get_all(
        session=db_session,
        filters=AnnotationsFilter(collection_ids=[copied.children[0].collection_id]),
    )
    assert copied_annotations.total_count == n_samples


def test_deep_copy__with_evaluation_runs(db_session: Session) -> None:
    # Arrange
    original = create_collection(session=db_session, collection_name="original")
    gt_collection = create_collection(
        session=db_session,
        collection_name="original__gt",
        parent_collection_id=original.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    pred_collection = create_collection(
        session=db_session,
        collection_name="original__pred",
        parent_collection_id=original.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    run = evaluation_run_resolver.create(
        session=db_session,
        evaluation_run_input=EvaluationRunCreate(
            name="my_eval",
            gt_annotation_collection_id=gt_collection.collection_id,
            dataset_id=gt_collection.dataset_id,
            pred_annotation_collection_id=pred_collection.collection_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
            config_json={"iou_threshold": 0.5},
        ),
    )

    # Act
    copied = dataset_resolver.deep_copy(
        session=db_session,
        dataset_id=original.dataset_id,
        copy_name="copied",
    )

    # Assert - exactly one evaluation run copied
    copied_runs = evaluation_run_resolver.get_all_by_dataset_id(
        session=db_session,
        dataset_id=copied.dataset_id,
    )
    assert len(copied_runs) == 1
    copied_run = copied_runs[0]

    # Assert - new ID assigned
    assert copied_run.id != run.id

    # Assert - fields preserved
    assert copied_run.name == "my_eval"
    assert copied_run.task_type == EvaluationTaskType.OBJECT_DETECTION
    assert copied_run.config_json == {"iou_threshold": 0.5}

    # Assert - collection FKs remapped to copied collections (not the originals)
    assert copied_run.gt_annotation_collection_id != gt_collection.collection_id
    assert copied_run.pred_annotation_collection_id != pred_collection.collection_id

    # Assert - referenced collections belong to the copied dataset
    copied_gt = collection_resolver.get_by_id(
        session=db_session, collection_id=copied_run.gt_annotation_collection_id
    )
    copied_pred = collection_resolver.get_by_id(
        session=db_session, collection_id=copied_run.pred_annotation_collection_id
    )
    assert copied_gt is not None
    assert copied_pred is not None
    assert copied_gt.dataset_id == copied.dataset_id
    assert copied_pred.dataset_id == copied.dataset_id

    # Assert - original run unchanged
    original_runs = evaluation_run_resolver.get_all_by_dataset_id(
        session=db_session,
        dataset_id=original.dataset_id,
    )
    assert len(original_runs) == 1
    assert original_runs[0].id == run.id
    assert original_runs[0].gt_annotation_collection_id == gt_collection.collection_id
    assert original_runs[0].pred_annotation_collection_id == pred_collection.collection_id


def test_deep_copy__with_evaluation_annotation_metrics(db_session: Session) -> None:
    # Arrange
    dataset = create_collection(session=db_session, collection_name="original")
    run = evaluation_sample_metric_helpers.create_run(
        session=db_session, collection_id=dataset.collection_id
    )
    image = create_image(session=db_session, collection_id=dataset.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=dataset.collection_id)
    pred_annotation = create_annotation(
        session=db_session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    create_annotation_metrics(
        session=db_session,
        run_id=run.id,
        true_positive_metric_stubs=[
            TruePositiveMetricStub(
                sample_id=image.sample_id,
                metrics={"iou": 0.8},
                gt_annotation_label_id=label.annotation_label_id,
            )
        ],
    )
    evaluation_annotation_metric_resolver.create_many(
        session=db_session,
        records=[
            # FP: only pred set
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                pred_annotation_id=pred_annotation.sample_id,
            ),
        ],
    )

    # Act
    copied = dataset_resolver.deep_copy(
        session=db_session,
        dataset_id=dataset.dataset_id,
        copy_name="copied",
    )

    # Assert - copied dataset has one evaluation run
    copied_runs = evaluation_run_resolver.get_all_by_dataset_id(
        session=db_session,
        dataset_id=copied.dataset_id,
    )
    assert len(copied_runs) == 1
    copied_run = copied_runs[0]
    assert copied_run.id != run.id

    # Assert - copied run has both annotation metrics
    copied_metrics = evaluation_annotation_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=copied_run.id,
    )
    assert len(copied_metrics) == 2

    original_metrics = evaluation_annotation_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=run.id,
    )
    assert len(original_metrics) == 2
    original_tp_metric = next(m for m in original_metrics if m.metric_name == "iou")

    # Assert - annotation IDs are remapped (not the originals)
    original_annotation_ids = {
        original_tp_metric.gt_annotation_id,
        original_tp_metric.pred_annotation_id,
        pred_annotation.sample_id,
    }
    copied_annotation_ids = (
        {m.gt_annotation_id for m in copied_metrics}
        | {m.pred_annotation_id for m in copied_metrics}
    ) - {None}
    assert original_annotation_ids.isdisjoint(copied_annotation_ids)

    # Assert - sample IDs are remapped
    original_sample_ids = {image.sample_id}
    copied_sample_ids = {m.sample_id for m in copied_metrics}
    assert original_sample_ids.isdisjoint(copied_sample_ids)

    # Assert - metric values preserved
    tp_metric = next(m for m in copied_metrics if m.metric_name == "iou")
    assert tp_metric.value == pytest.approx(0.8)
    assert tp_metric.gt_annotation_id is not None
    assert tp_metric.pred_annotation_id is not None

    fp_metric = next(m for m in copied_metrics if m.metric_name is None)
    assert fp_metric.gt_annotation_id is None
    assert fp_metric.pred_annotation_id is not None

    # Assert - original run metrics are untouched
    assert len(original_metrics) == 2
