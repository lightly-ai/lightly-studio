from typing import Any
from uuid import UUID

from sqlalchemy.orm import Mapped
from sqlmodel import Session, col, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationTable
from lightly_studio.models.annotation.segmentation import SegmentationAnnotationTable
from lightly_studio.models.metadata import SampleMetadataTable
from lightly_studio.models.sample import SampleTable, SampleTagLinkTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.models.temporal_span import TemporalSpanTable
from lightly_studio.resolvers import annotation_resolver, evaluation_annotation_metric_resolver
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_embedding_model,
    create_image,
    create_sample_embedding,
    create_tag,
)
from tests.resolvers.evaluation_sample_metric_resolver import (
    helpers as evaluation_sample_metric_helpers,
)
from tests.resolvers.evaluation_sample_metric_resolver.helpers import (
    AnnotationMetricStub,
    create_annotation_metrics,
)


def test_delete_annotations_by_ids(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=dataset.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=dataset.collection_id)
    classification, object_detection, segmentation, kept = create_annotations(
        session=db_session,
        collection_id=dataset.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
                start_time_s=1.5,
                end_time_s=4.0,
            ),
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
            ),
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.SEGMENTATION_MASK,
                segmentation_mask=[1, 2, 3, 4],
            ),
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
            ),
        ],
    )
    deleted_ids = [classification.sample_id, object_detection.sample_id, segmentation.sample_id]

    deleted_count = annotation_resolver.delete_annotations_by_ids(
        session=db_session,
        annotation_collection_id=kept.sample.collection_id,
        annotation_ids=deleted_ids,
    )

    assert deleted_count == 3
    assert (
        _count_rows(
            session=db_session, column=col(AnnotationBaseTable.sample_id), sample_ids=deleted_ids
        )
        == 0
    )
    assert (
        _count_rows(
            session=db_session,
            column=col(ObjectDetectionAnnotationTable.sample_id),
            sample_ids=deleted_ids,
        )
        == 0
    )
    assert (
        _count_rows(
            session=db_session,
            column=col(SegmentationAnnotationTable.sample_id),
            sample_ids=deleted_ids,
        )
        == 0
    )
    assert (
        _count_rows(
            session=db_session, column=col(TemporalSpanTable.sample_id), sample_ids=deleted_ids
        )
        == 0
    )
    assert (
        _count_rows(session=db_session, column=col(SampleTable.sample_id), sample_ids=deleted_ids)
        == 0
    )
    # The annotation that was not requested is kept.
    assert annotation_resolver.get_by_id(db_session, kept.sample_id) is not None


def test_delete_annotations_by_ids__deletes_tag_links_embeddings_and_metadata(
    db_session: Session,
) -> None:
    dataset = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=dataset.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=dataset.collection_id)
    annotation = create_annotation(
        session=db_session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    annotation_collection_id = annotation.sample.collection_id
    tag = create_tag(
        session=db_session,
        collection_id=annotation_collection_id,
        tag_name="annotation-tag",
        kind="annotation",
    )
    annotation.sample.tags.append(tag)
    db_session.add(annotation.sample)
    embedding_model = create_embedding_model(
        session=db_session, collection_id=annotation_collection_id
    )
    create_sample_embedding(
        session=db_session,
        sample_id=annotation.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[0.1] * embedding_model.embedding_dimension,
    )
    db_session.add(
        SampleMetadataTable(
            sample_id=annotation.sample_id,
            data={"score": 0.5},
            metadata_schema={"score": "float"},
        )
    )
    db_session.commit()
    annotation_ids = [annotation.sample_id]

    deleted_count = annotation_resolver.delete_annotations_by_ids(
        session=db_session,
        annotation_collection_id=annotation_collection_id,
        annotation_ids=annotation_ids,
    )

    assert deleted_count == 1
    assert (
        _count_rows(
            session=db_session, column=col(SampleTagLinkTable.sample_id), sample_ids=annotation_ids
        )
        == 0
    )
    assert (
        _count_rows(
            session=db_session,
            column=col(SampleEmbeddingTable.sample_id),
            sample_ids=annotation_ids,
        )
        == 0
    )
    assert (
        _count_rows(
            session=db_session, column=col(SampleMetadataTable.sample_id), sample_ids=annotation_ids
        )
        == 0
    )
    assert (
        _count_rows(
            session=db_session, column=col(SampleTable.sample_id), sample_ids=annotation_ids
        )
        == 0
    )


def test_delete_annotations_by_ids__ignores_other_collection_and_unknown_ids(
    db_session: Session,
) -> None:
    dataset = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=dataset.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=dataset.collection_id)
    ground_truth = create_annotation(
        session=db_session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_collection_name="ground_truth",
    )
    prediction = create_annotation(
        session=db_session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_collection_name="predictions",
    )
    ground_truth_id = ground_truth.sample_id
    prediction_id = prediction.sample_id
    unknown_id = UUID("12345678-1234-5678-1234-567812345678")

    deleted_count = annotation_resolver.delete_annotations_by_ids(
        session=db_session,
        annotation_collection_id=ground_truth.sample.collection_id,
        annotation_ids=[ground_truth_id, prediction_id, unknown_id],
    )

    assert deleted_count == 1
    assert annotation_resolver.get_by_id(db_session, ground_truth_id) is None
    assert annotation_resolver.get_by_id(db_session, prediction_id) is not None


def test_delete_annotations_by_ids__deletes_evaluation_annotation_metrics(
    db_session: Session,
) -> None:
    dataset = create_collection(session=db_session)
    run = evaluation_sample_metric_helpers.create_run(
        session=db_session, collection_id=dataset.collection_id
    )
    image = create_image(session=db_session, collection_id=dataset.collection_id)
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

    annotation_resolver.delete_annotations_by_ids(
        session=db_session,
        annotation_collection_id=gt_annotation.sample.collection_id,
        annotation_ids=[gt_annotation.sample_id],
    )

    annotation_metrics = evaluation_annotation_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session, evaluation_run_id=run.id
    )
    assert annotation_metrics == []


def test_delete_annotations_by_ids__empty_ids(db_session: Session) -> None:
    dataset = create_collection(session=db_session)

    deleted_count = annotation_resolver.delete_annotations_by_ids(
        session=db_session,
        annotation_collection_id=dataset.collection_id,
        annotation_ids=[],
    )

    assert deleted_count == 0


def _count_rows(session: Session, column: Mapped[Any], sample_ids: list[UUID]) -> int:
    return len(session.exec(select(column).where(column.in_(sample_ids))).all())
