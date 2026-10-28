from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlmodel import Session, SQLModel, col, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.annotation.cuboid_3d import Cuboid3DAnnotationTable
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationTable
from lightly_studio.models.annotation.segmentation import SegmentationAnnotationTable
from lightly_studio.models.caption import CaptionTable
from lightly_studio.models.embedding_plot import EmbeddingPlotTable
from lightly_studio.models.evaluation_run import EvaluationRunCreate, EvaluationTaskType
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable, SampleTagLinkTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.models.temporal_span import TemporalSpanTable
from lightly_studio.resolvers import (
    annotation_resolver,
    evaluation_annotation_metric_resolver,
    evaluation_run_resolver,
    evaluation_sample_metric_resolver,
)
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_caption,
    create_collection,
    create_embedding_model,
    create_groups,
    create_image,
    create_sample_embedding,
    create_tag,
    cuboid_create,
)
from tests.resolvers.evaluation_sample_metric_resolver import (
    helpers as evaluation_sample_metric_helpers,
)
from tests.resolvers.evaluation_sample_metric_resolver.helpers import (
    AnnotationMetricStub,
    SampleMetricStub,
    create_annotation_metrics,
    create_sample_metrics,
)


@pytest.mark.parametrize(
    ("annotation_type", "extra_fields", "detail_table"),
    [
        (AnnotationType.OBJECT_DETECTION, {}, ObjectDetectionAnnotationTable),
        (
            AnnotationType.SEGMENTATION_MASK,
            {"segmentation_mask": [1, 2, 3, 4]},
            SegmentationAnnotationTable,
        ),
        (
            AnnotationType.CLASSIFICATION,
            {"start_time_s": 1.5, "end_time_s": 4.0},
            TemporalSpanTable,
        ),
    ],
)
def test_delete_annotations_by_ids(
    db_session: Session,
    annotation_type: AnnotationType,
    extra_fields: dict[str, Any],
    detail_table: type[SQLModel],
) -> None:
    image = _create_image_in_new_collection(session=db_session)
    label = create_annotation_label(
        session=db_session, root_collection_id=image.sample.collection_id
    )
    annotation_details = AnnotationDetails(
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=annotation_type,
        **extra_fields,
    )
    to_delete, to_keep = create_annotations(
        session=db_session,
        collection_id=image.sample.collection_id,
        annotations=[annotation_details, annotation_details],
    )
    to_delete_id, to_keep_id = to_delete.sample_id, to_keep.sample_id
    image_id = image.sample_id
    assert db_session.get(detail_table, to_delete_id) is not None

    deleted_count = annotation_resolver.delete_annotations_by_ids(
        session=db_session, annotation_ids=[to_delete_id]
    )

    assert deleted_count == 1
    assert db_session.get(detail_table, to_delete_id) is None
    assert db_session.get(AnnotationBaseTable, to_delete_id) is None
    assert db_session.get(SampleTable, to_delete_id) is None
    assert db_session.get(detail_table, to_keep_id) is not None
    assert db_session.get(AnnotationBaseTable, to_keep_id) is not None
    assert db_session.get(SampleTable, to_keep_id) is not None
    assert db_session.get(SampleTable, image_id) is not None


def test_delete_annotations_by_ids__cuboid_3d(db_session: Session) -> None:
    parent_collection_id, group_ids = create_groups(session=db_session)
    label = create_annotation_label(session=db_session, root_collection_id=parent_collection_id)
    to_delete, to_keep = annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=parent_collection_id,
        annotations=[
            cuboid_create(
                parent_sample_id=group_ids[0], annotation_label_id=label.annotation_label_id
            ),
            cuboid_create(
                parent_sample_id=group_ids[0], annotation_label_id=label.annotation_label_id
            ),
        ],
    )

    deleted_count = annotation_resolver.delete_annotations_by_ids(
        session=db_session, annotation_ids=[to_delete]
    )

    assert deleted_count == 1
    assert db_session.get(Cuboid3DAnnotationTable, to_delete) is None
    assert db_session.get(AnnotationBaseTable, to_delete) is None
    assert db_session.get(SampleTable, to_delete) is None
    assert db_session.get(Cuboid3DAnnotationTable, to_keep) is not None
    assert db_session.get(AnnotationBaseTable, to_keep) is not None


def test_delete_annotations_by_ids__deletes_tag_links_and_embeddings(
    db_session: Session,
) -> None:
    image = _create_image_in_new_collection(session=db_session)
    to_delete, to_keep = _create_object_detections(session=db_session, image=image, count=2)
    annotation_collection_id = to_delete.sample.collection_id
    tag = create_tag(
        session=db_session, collection_id=annotation_collection_id, tag_name="annotation-tag"
    )
    embedding_model = create_embedding_model(
        session=db_session, collection_id=annotation_collection_id, embedding_dimension=2
    )
    for annotation in (to_delete, to_keep):
        annotation.sample.tags.append(tag)
        db_session.add(annotation.sample)
        create_sample_embedding(
            session=db_session,
            sample_id=annotation.sample_id,
            embedding_model_id=embedding_model.embedding_model_id,
            embedding=[0.1, 0.2],
        )
    db_session.commit()
    to_delete_id, to_keep_id = to_delete.sample_id, to_keep.sample_id

    plot = EmbeddingPlotTable(
        collection_id=annotation_collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
        is_dirty=False,
    )
    plot = db_session.merge(plot)
    db_session.commit()

    annotation_resolver.delete_annotations_by_ids(session=db_session, annotation_ids=[to_delete_id])

    assert _get_tag_link_sample_ids(session=db_session) == [to_keep_id]
    db_session.refresh(plot)
    assert plot.is_dirty is True
    assert _get_embedding_sample_ids(session=db_session) == [to_keep_id]
    assert db_session.get(SampleTable, to_delete_id) is None


def test_delete_annotations_by_ids__deletes_captions(db_session: Session) -> None:
    image = _create_image_in_new_collection(session=db_session)
    to_delete, to_keep = _create_object_detections(session=db_session, image=image, count=2)
    to_delete_id, to_keep_id = to_delete.sample_id, to_keep.sample_id
    annotation_collection_id = to_delete.sample.collection_id
    deleted_caption_id = create_caption(
        session=db_session, collection_id=annotation_collection_id, parent_sample_id=to_delete_id
    ).sample_id
    kept_caption_id = create_caption(
        session=db_session, collection_id=annotation_collection_id, parent_sample_id=to_keep_id
    ).sample_id
    image_caption_id = create_caption(
        session=db_session,
        collection_id=image.sample.collection_id,
        parent_sample_id=image.sample_id,
    ).sample_id

    annotation_resolver.delete_annotations_by_ids(session=db_session, annotation_ids=[to_delete_id])

    assert db_session.get(CaptionTable, deleted_caption_id) is None
    assert db_session.get(SampleTable, deleted_caption_id) is None
    assert db_session.get(CaptionTable, kept_caption_id) is not None
    assert db_session.get(CaptionTable, image_caption_id) is not None
    assert db_session.get(SampleTable, to_delete_id) is None


def test_delete_annotations_by_ids__delete_samples_false_keeps_sample(db_session: Session) -> None:
    # The annotation label update deletes the annotation but reuses its sample.
    image = _create_image_in_new_collection(session=db_session)
    (annotation,) = _create_object_detections(session=db_session, image=image, count=1)
    tag = create_tag(
        session=db_session, collection_id=annotation.sample.collection_id, tag_name="tag"
    )
    annotation.sample.tags.append(tag)
    db_session.add(annotation.sample)
    db_session.commit()
    annotation_id = annotation.sample_id
    plot = EmbeddingPlotTable(
        collection_id=annotation.sample.collection_id, embedding_model_id=uuid4(), is_dirty=False
    )
    plot = db_session.merge(plot)
    db_session.commit()

    deleted_count = annotation_resolver.delete_annotations_by_ids(
        session=db_session, annotation_ids=[annotation_id], delete_samples=False
    )

    assert deleted_count == 1
    assert db_session.get(AnnotationBaseTable, annotation_id) is None
    assert db_session.get(ObjectDetectionAnnotationTable, annotation_id) is None
    assert db_session.get(SampleTable, annotation_id) is not None
    assert _get_tag_link_sample_ids(session=db_session) == [annotation_id]
    db_session.refresh(plot)
    assert plot.is_dirty is False


def test_delete_annotations_by_ids__multiple(db_session: Session) -> None:
    image = _create_image_in_new_collection(session=db_session)
    annotation_ids = [
        annotation.sample_id
        for annotation in _create_object_detections(session=db_session, image=image, count=3)
    ]

    deleted_count = annotation_resolver.delete_annotations_by_ids(
        session=db_session,
        annotation_ids=[annotation_ids[0], annotation_ids[2]],
    )

    assert deleted_count == 2
    remaining_ids = db_session.exec(select(AnnotationBaseTable.sample_id)).all()
    assert remaining_ids == [annotation_ids[1]]


def test_delete_annotations_by_ids__ignores_missing_and_duplicate_ids(
    db_session: Session,
) -> None:
    image = _create_image_in_new_collection(session=db_session)
    (annotation,) = _create_object_detections(session=db_session, image=image, count=1)
    annotation_id = annotation.sample_id

    deleted_count = annotation_resolver.delete_annotations_by_ids(
        session=db_session,
        annotation_ids=[annotation_id, annotation_id, uuid4()],
    )

    assert deleted_count == 1
    assert db_session.get(AnnotationBaseTable, annotation_id) is None


def test_delete_annotations_by_ids__empty(db_session: Session) -> None:
    image = _create_image_in_new_collection(session=db_session)
    (annotation,) = _create_object_detections(session=db_session, image=image, count=1)

    deleted_count = annotation_resolver.delete_annotations_by_ids(
        session=db_session, annotation_ids=[]
    )

    assert deleted_count == 0
    assert db_session.get(AnnotationBaseTable, annotation.sample_id) is not None


def test_delete_annotations_by_ids__deletes_evaluation_metrics(db_session: Session) -> None:
    image = _create_image_in_new_collection(session=db_session)
    run = evaluation_sample_metric_helpers.create_run(
        session=db_session, collection_id=image.sample.collection_id
    )
    pred_annotation, gt_annotation = _create_object_detections(
        session=db_session, image=image, count=2
    )
    create_annotation_metrics(
        session=db_session,
        run_id=run.id,
        annotation_metrics=[
            AnnotationMetricStub(
                sample_id=image.sample_id,
                metric_name="iou",
                value=0.75,
                pred_annotation_id=pred_annotation.sample_id,
                gt_annotation_id=gt_annotation.sample_id,
            )
        ],
    )
    create_sample_metrics(
        session=db_session,
        run_id=run.id,
        sample_metrics=[SampleMetricStub(sample_id=image.sample_id, metrics={"score": 0.5})],
    )

    pred_annotation_id = pred_annotation.sample_id

    annotation_resolver.delete_annotations_by_ids(
        session=db_session, annotation_ids=[gt_annotation.sample_id]
    )

    assert (
        evaluation_annotation_metric_resolver.get_all_by_evaluation_run_id(
            session=db_session, evaluation_run_id=run.id
        )
        == []
    )
    assert (
        evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
            session=db_session, evaluation_run_id=run.id
        )
        == []
    )
    assert db_session.get(AnnotationBaseTable, pred_annotation_id) is not None


def test_delete_annotations_by_ids__marks_evaluation_run_stale(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    annotation_details = [
        AnnotationDetails(sample_id=image.sample_id, annotation_label_id=label.annotation_label_id)
    ]
    gt_annotation = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=annotation_details,
        collection_name="ground_truth",
    )[0]
    pred_annotation = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=annotation_details,
        collection_name="predictions",
    )[0]
    run = evaluation_run_resolver.create(
        session=db_session,
        evaluation_run_input=EvaluationRunCreate(
            name="run",
            gt_annotation_collection_id=gt_annotation.annotation_collection_id,
            pred_annotation_collection_id=pred_annotation.annotation_collection_id,
            dataset_id=collection.dataset_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )
    assert run.stale_since is None

    annotation_resolver.delete_annotations_by_ids(
        session=db_session, annotation_ids=[pred_annotation.sample_id]
    )

    refreshed = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run.id)
    assert refreshed is not None
    assert refreshed.stale_since is not None


def _create_image_in_new_collection(session: Session) -> ImageTable:
    collection = create_collection(session=session)
    return create_image(session=session, collection_id=collection.collection_id)


def _create_object_detections(
    session: Session, image: ImageTable, count: int
) -> list[AnnotationBaseTable]:
    label = create_annotation_label(session=session, root_collection_id=image.sample.collection_id)
    return create_annotations(
        session=session,
        collection_id=image.sample.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id, annotation_label_id=label.annotation_label_id
            )
            for _ in range(count)
        ],
    )


def _get_tag_link_sample_ids(session: Session) -> list[UUID | None]:
    return list(session.exec(select(SampleTagLinkTable.sample_id)).all())


def _get_embedding_sample_ids(session: Session) -> list[UUID]:
    return list(
        session.exec(
            select(SampleEmbeddingTable.sample_id).order_by(col(SampleEmbeddingTable.sample_id))
        ).all()
    )
