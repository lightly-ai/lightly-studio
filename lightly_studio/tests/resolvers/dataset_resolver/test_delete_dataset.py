"""Tests for delete_dataset resolver."""

import importlib
import uuid

import pytest
from sqlmodel import Session, col, select

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import SampleType
from lightly_studio.models.evaluation_annotation_metric import EvaluationAnnotationMetricCreate
from lightly_studio.models.evaluation_run import EvaluationRunCreate, EvaluationTaskType
from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricCreate
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTagLinkTable
from lightly_studio.resolvers import (
    annotation_label_resolver,
    collection_resolver,
    dataset_resolver,
    evaluation_annotation_metric_resolver,
    evaluation_run_resolver,
    evaluation_sample_metric_resolver,
    metadata_resolver,
    sample_embedding_resolver,
    sample_resolver,
    tag_resolver,
)
from lightly_studio.utils import batching
from tests.helpers_resolvers import (
    AnnotationDetails,
    ImageStub,
    create_annotation,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_embedding_model,
    create_image,
    create_images,
    create_sample_embedding,
    create_tag,
)
from tests.resolvers.evaluation_sample_metric_resolver import (
    helpers as evaluation_sample_metric_helpers,
)
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames

# The dataset_resolver package shadows the submodule name with the delete_dataset
# function, so import the module explicitly to reach its private chunking helper.
delete_dataset_module = importlib.import_module(
    "lightly_studio.resolvers.dataset_resolver.delete_dataset"
)


def test_delete_dataset__empty_collection(db_session: Session) -> None:
    # Arrange
    dataset = create_collection(session=db_session, collection_name="to_delete")
    collection_id = dataset.collection_id  # Capture before delete

    # Act
    dataset_resolver.delete_dataset(
        session=db_session,
        dataset_id=dataset.dataset_id,
    )

    # Assert - collection deleted
    assert collection_resolver.get_by_id(session=db_session, collection_id=collection_id) is None


def test_delete_dataset__with_images_and_annotations(db_session: Session) -> None:
    # Arrange
    dataset = create_collection(session=db_session, collection_name="to_delete")
    collection_id = dataset.collection_id  # Capture before delete
    img = create_image(session=db_session, collection_id=collection_id, file_path_abs="/a.png")
    label = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    )
    label_id = label.annotation_label_id  # Capture before delete
    create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=img.sample_id,
                annotation_label_id=label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
            )
        ],
    )
    root = collection_resolver.get_by_id(session=db_session, collection_id=collection_id)
    assert root is not None
    child_collection_id = root.children[0].collection_id

    # Act
    dataset_resolver.delete_dataset(
        session=db_session,
        dataset_id=dataset.dataset_id,
    )

    # Assert - collection, annotations, and labels deleted
    assert collection_resolver.get_by_id(session=db_session, collection_id=collection_id) is None
    assert (
        collection_resolver.get_by_id(session=db_session, collection_id=child_collection_id) is None
    )
    assert annotation_label_resolver.get_by_id(session=db_session, label_id=label_id) is None


def test_delete_dataset__with_video_and_frames(db_session: Session) -> None:
    # Arrange
    root_collection_id = create_collection(
        session=db_session, collection_name="root_dataset", sample_type=SampleType.VIDEO
    ).collection_id
    create_video_with_frames(
        session=db_session,
        collection_id=root_collection_id,
        video=VideoStub(path="/path/to/sample1.mp4"),
    )
    # Refetch root after adding frames.
    root = collection_resolver.get_by_id(session=db_session, collection_id=root_collection_id)
    assert root is not None
    child_collection_id = root.children[0].collection_id  # Capture before delete

    # Act
    dataset_resolver.delete_dataset(
        session=db_session,
        dataset_id=root.dataset_id,
    )

    # Assert - entire hierarchy deleted
    assert (
        collection_resolver.get_by_id(session=db_session, collection_id=root_collection_id) is None
    )
    assert (
        collection_resolver.get_by_id(session=db_session, collection_id=child_collection_id) is None
    )


def test_delete_dataset__with_metadata(db_session: Session) -> None:
    # Arrange
    dataset = create_collection(session=db_session, collection_name="to_delete")
    collection_id = dataset.collection_id  # Capture before delete
    img = create_image(session=db_session, collection_id=collection_id, file_path_abs="/test.png")
    sample_id = img.sample_id  # Capture before delete
    img.sample["temperature"] = 25
    img.sample["location"] = "city"

    # Act
    dataset_resolver.delete_dataset(
        session=db_session,
        dataset_id=dataset.dataset_id,
    )

    # Assert - collection and metadata deleted
    assert collection_resolver.get_by_id(session=db_session, collection_id=collection_id) is None
    assert metadata_resolver.get_by_sample_id(session=db_session, sample_id=sample_id) is None


def test_delete_dataset__with_embeddings(db_session: Session) -> None:
    # Arrange
    dataset = create_collection(session=db_session, collection_name="to_delete")
    collection_id = dataset.collection_id  # Capture before delete
    img = create_image(session=db_session, collection_id=collection_id, file_path_abs="/a.png")

    embedding_model = create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="test_model",
        embedding_dimension=512,
    )
    embedding_model_id = embedding_model.embedding_model_id  # Capture before delete
    create_sample_embedding(
        session=db_session,
        sample_id=img.sample_id,
        embedding_model_id=embedding_model_id,
        embedding=[1.0, 2.0, 3.0],
    )

    # Act
    dataset_resolver.delete_dataset(
        session=db_session,
        dataset_id=dataset.dataset_id,
    )

    # Assert - collection deleted, embeddings deleted
    assert collection_resolver.get_by_id(session=db_session, collection_id=collection_id) is None
    embeddings = sample_embedding_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        embedding_model_id=embedding_model_id,
    )
    assert len(embeddings) == 0


def test_delete_dataset__with_tags(db_session: Session) -> None:
    # Arrange
    dataset = create_collection(session=db_session, collection_name="to_delete")
    collection_id = dataset.collection_id  # Capture before delete
    img = create_image(session=db_session, collection_id=collection_id, file_path_abs="/a.png")
    tag = create_tag(session=db_session, collection_id=collection_id, tag_name="my_tag")
    tag_id = tag.tag_id  # Capture before delete
    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag_id, sample=img.sample)

    # Act
    dataset_resolver.delete_dataset(
        session=db_session,
        dataset_id=dataset.dataset_id,
    )

    # Assert - collection and tags deleted
    assert collection_resolver.get_by_id(session=db_session, collection_id=collection_id) is None
    assert tag_resolver.get_by_id(session=db_session, tag_id=tag_id) is None


def test_delete_dataset__does_not_affect_other_datasets(db_session: Session) -> None:
    # Arrange - create two datasets
    dataset_to_delete = create_collection(session=db_session, collection_name="to_delete")
    delete_collection_id = dataset_to_delete.collection_id  # Capture before delete
    create_image(session=db_session, collection_id=delete_collection_id, file_path_abs="/a.png")
    tag_to_delete = create_tag(
        session=db_session, collection_id=delete_collection_id, tag_name="tag_delete"
    )
    delete_tag_id = tag_to_delete.tag_id  # Capture before delete

    other_dataset = create_collection(session=db_session, collection_name="other")
    other_collection_id = other_dataset.collection_id  # Capture before delete
    other_image = create_image(
        session=db_session, collection_id=other_collection_id, file_path_abs="/other.png"
    )
    other_sample_id = other_image.sample_id  # Capture before delete
    other_tag = create_tag(
        session=db_session, collection_id=other_collection_id, tag_name="tag_other"
    )
    other_tag_id = other_tag.tag_id  # Capture before delete

    # Act
    dataset_resolver.delete_dataset(
        session=db_session,
        dataset_id=dataset_to_delete.dataset_id,
    )

    # Assert - deleted dataset is gone
    assert (
        collection_resolver.get_by_id(session=db_session, collection_id=delete_collection_id)
        is None
    )
    assert tag_resolver.get_by_id(session=db_session, tag_id=delete_tag_id) is None

    # Assert - other dataset is intact
    assert (
        collection_resolver.get_by_id(session=db_session, collection_id=other_collection_id)
        is not None
    )
    assert tag_resolver.get_by_id(session=db_session, tag_id=other_tag_id) is not None

    other_samples = sample_resolver.get_filtered_samples(
        session=db_session,
        collection_id=other_collection_id,
    )
    assert other_samples.total_count == 1
    assert other_samples.samples[0].sample_id == other_sample_id


def test_delete_dataset__with_evaluation_sample_metrics(db_session: Session) -> None:
    # Arrange
    dataset = create_collection(session=db_session, collection_name="to_delete")
    run, image = evaluation_sample_metric_helpers.create_run_and_image(
        db_session, dataset_collection_id=dataset.collection_id
    )
    run_id = run.id  # Capture before delete
    evaluation_sample_metric_resolver.create_many(
        session=db_session,
        records=[
            EvaluationSampleMetricCreate(
                evaluation_run_id=run_id,
                sample_id=image.sample_id,
                metric_name="precision",
                value=0.9,
            )
        ],
    )

    # Act
    dataset_resolver.delete_dataset(
        session=db_session,
        dataset_id=dataset.dataset_id,
    )

    # Assert - evaluation run and its metrics deleted
    assert evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run_id) is None
    metrics = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=run_id,
    )
    assert metrics == []


def test_delete_dataset__with_evaluation_runs(db_session: Session) -> None:
    # Arrange
    dataset = create_collection(session=db_session, collection_name="to_delete")
    gt_collection = create_collection(
        session=db_session,
        collection_name="to_delete__gt",
        parent_collection_id=dataset.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    pred_collection = create_collection(
        session=db_session,
        collection_name="to_delete__pred",
        parent_collection_id=dataset.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    run = evaluation_run_resolver.create(
        session=db_session,
        evaluation_run_input=EvaluationRunCreate(
            name="my_eval",
            gt_annotation_collection_id=gt_collection.collection_id,
            pred_annotation_collection_id=pred_collection.collection_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )
    run_id = run.id  # Capture before delete
    dataset_collection_id = dataset.collection_id  # Capture before delete

    # Act
    dataset_resolver.delete_dataset(
        session=db_session,
        dataset_id=dataset.dataset_id,
    )

    # Assert - evaluation run and its metrics deleted
    assert evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run_id) is None
    metrics = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=run_id,
    )
    assert metrics == []
    # Assert - dataset and evaluation run deleted
    assert (
        collection_resolver.get_by_id(session=db_session, collection_id=dataset_collection_id)
        is None
    )
    assert evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run_id) is None


def test_delete_dataset__with_evaluation_annotation_metrics(db_session: Session) -> None:
    # Arrange
    dataset = create_collection(session=db_session, collection_name="to_delete")
    run, image = evaluation_sample_metric_helpers.create_run_and_image(
        db_session, dataset_collection_id=dataset.collection_id
    )
    run_id = run.id  # Capture before delete
    label = create_annotation_label(session=db_session, root_collection_id=dataset.collection_id)
    gt_annotation = create_annotation(
        session=db_session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    pred_annotation = create_annotation(
        session=db_session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    evaluation_annotation_metric_resolver.create_many(
        session=db_session,
        records=[
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run_id,
                sample_id=image.sample_id,
                gt_annotation_id=gt_annotation.sample_id,
                pred_annotation_id=pred_annotation.sample_id,
                metric_name="iou",
                value=0.8,
            ),
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run_id,
                sample_id=image.sample_id,
                pred_annotation_id=pred_annotation.sample_id,
            ),
        ],
    )

    # Act
    dataset_resolver.delete_dataset(
        session=db_session,
        dataset_id=dataset.dataset_id,
    )

    # Assert - evaluation run and its annotation metrics deleted
    assert evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run_id) is None
    metrics = evaluation_annotation_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=run_id,
    )
    assert metrics == []


def test_delete_dataset__raises_for_nonexistent_dataset(db_session: Session) -> None:
    # Arrange
    nonexistent_id = uuid.uuid4()

    # Act & Assert
    with pytest.raises(ValueError, match="not found"):
        dataset_resolver.delete_dataset(
            session=db_session,
            dataset_id=nonexistent_id,
        )


def test_delete_sample_tag_links__exceeds_postgres_param_limit(db_session: Session) -> None:
    # Arrange - more ids than PostgreSQL's 65,535 single-statement bind-param cap.
    # The param-count error fires at send time regardless of matching rows, so this
    # reproduces the bug cheaply: pre-fix it raises under --postgres, post-fix it
    # passes on both backends.
    sample_ids = [uuid.uuid4() for _ in range(70_000)]

    # Act
    delete_dataset_module._delete_sample_tag_links(session=db_session, sample_ids=sample_ids)
    db_session.commit()

    # Assert - the chunked delete ran without exceeding the parameter limit.
    remaining = db_session.exec(select(SampleTagLinkTable)).all()
    assert remaining == []


def test_delete_images__deletes_across_batches(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange - 5 rows with batch size 2 -> 3 batches (2 + 2 + 1).
    monkeypatch.setattr(batching, "DEFAULT_BATCH_SIZE", 2)
    collection_id = create_collection(session=db_session, collection_name="batchy").collection_id
    images = create_images(
        db_session=db_session,
        collection_id=collection_id,
        images=[ImageStub(path=f"/b/{i}.png") for i in range(5)],
    )
    sample_ids = [image.sample_id for image in images]

    # Act
    delete_dataset_module._delete_images(session=db_session, sample_ids=sample_ids)
    db_session.commit()

    # Assert - all rows removed across every batch.
    remaining = db_session.exec(
        select(ImageTable).where(col(ImageTable.sample_id).in_(sample_ids))
    ).all()
    assert remaining == []
