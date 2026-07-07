from uuid import UUID

import pytest
from sqlmodel import Session, col, select

from lightly_studio.models.sample import SampleTable, SampleTagLinkTable
from lightly_studio.resolvers import (
    annotation_resolver,
    evaluation_annotation_metric_resolver,
    evaluation_sample_metric_resolver,
)
from tests.conftest import AnnotationsTestData
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
    create_tag,
)
from tests.resolvers.evaluation_sample_metric_resolver import (
    helpers as evaluation_sample_metric_helpers,
)
from tests.resolvers.evaluation_sample_metric_resolver.helpers import (
    AnnotationMetricStub,
    SampleMetricStub,
    TruePositiveMetricStub,
    create_annotation_metrics,
    create_sample_metrics,
)


def test_delete_annotation__success(
    db_session: Session,
    annotations_test_data: AnnotationsTestData,  # noqa: ARG001
) -> None:
    """Test deleting an annotation."""
    annotations = annotation_resolver.get_all(db_session).annotations

    annotation_ids_to_delete = [
        annotations[0].sample_id,  # classification
        annotations[3].sample_id,  # object detection
        annotations[6].sample_id,  # segmentation mask
    ]

    for annotation_id in annotation_ids_to_delete:
        annotation_resolver.delete_annotation(db_session, annotation_id)

        # Verify the change persisted in the database.
        deleted_annotation = annotation_resolver.get_by_id(db_session, annotation_id)
        assert deleted_annotation is None


def test_delete_annotation__raises_error_when_annotation_not_found(
    db_session: Session,
) -> None:
    """Test that delete_annotation raises ValueError when annotation is not found."""
    non_existent_annotation_id = UUID("12345678-1234-5678-1234-567812345678")

    # Call the resolver and expect ValueError
    with pytest.raises(ValueError, match=f"Annotation {non_existent_annotation_id} not found"):
        annotation_resolver.delete_annotation(db_session, non_existent_annotation_id)


def test_delete_annotation__deletes_sample_tag_links(
    db_session: Session,
    annotations_test_data: AnnotationsTestData,
) -> None:
    """Test deleting an annotation also removes tag links for its sample."""
    annotation = annotations_test_data.annotations[0]
    annotation_collection_id = annotation.sample.collection_id
    tag = create_tag(
        session=db_session,
        collection_id=annotation_collection_id,
        tag_name="annotation-tag",
        kind="annotation",
    )
    annotation.sample.tags.append(tag)
    db_session.add(annotation.sample)
    db_session.commit()

    # Verify there is at least one link before deletion.
    links_before = db_session.exec(
        select(SampleTagLinkTable).where(col(SampleTagLinkTable.sample_id) == annotation.sample_id)
    ).all()
    assert links_before

    annotation_resolver.delete_annotation(db_session, annotation.sample_id)

    # Verify both annotation and sample-tag links were deleted.
    assert annotation_resolver.get_by_id(db_session, annotation.sample_id) is None
    links_after = db_session.exec(
        select(SampleTagLinkTable).where(col(SampleTagLinkTable.sample_id) == annotation.sample_id)
    ).all()
    assert not links_after
    assert db_session.get(SampleTable, annotation.sample_id) is None


def test_delete_annotation__deletes_evaluation_annotation_metrics(
    db_session: Session,
) -> None:
    """Test deleting an annotation removes invalidated evaluation rows."""
    dataset = create_collection(session=db_session)
    run = evaluation_sample_metric_helpers.create_run(
        session=db_session,
        collection_id=dataset.collection_id,
    )
    image = create_image(session=db_session, collection_id=dataset.collection_id)
    collection_id = dataset.collection_id
    label = create_annotation_label(session=db_session, root_collection_id=collection_id)
    pred_annotation = create_annotation(
        session=db_session,
        collection_id=collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    gt_annotation = create_annotation(
        session=db_session,
        collection_id=collection_id,
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
    create_sample_metrics(
        session=db_session,
        run_id=run.id,
        sample_metrics=[SampleMetricStub(sample_id=image.sample_id, metrics={"score": 0.5})],
    )

    annotation_resolver.delete_annotation(db_session, gt_annotation.sample_id)

    annotation_metrics = evaluation_annotation_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=run.id,
    )
    sample_metrics = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=run.id,
    )
    assert annotation_metrics == []
    assert sample_metrics == []


def test_delete_annotation__preserves_other_run_sample_metrics(
    db_session: Session,
) -> None:
    """Test deleting an annotation only invalidates sample metrics for affected runs."""
    dataset = create_collection(session=db_session)
    run = evaluation_sample_metric_helpers.create_run(
        session=db_session,
        collection_id=dataset.collection_id,
        name="run1",
    )
    image = create_image(session=db_session, collection_id=dataset.collection_id)
    other_run = evaluation_sample_metric_helpers.create_run(
        session=db_session,
        collection_id=dataset.collection_id,
        name="run2",
    )

    label = create_annotation_label(
        session=db_session,
        root_collection_id=dataset.collection_id,
    )
    pred_annotation = create_annotation(
        session=db_session,
        collection_id=run.pred_annotation_collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    gt_annotation = create_annotation(
        session=db_session,
        collection_id=run.gt_annotation_collection_id,
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
    create_sample_metrics(
        session=db_session,
        run_id=run.id,
        sample_metrics=[SampleMetricStub(sample_id=image.sample_id, metrics={"score": 0.5})],
    )
    create_annotation_metrics(
        session=db_session,
        run_id=other_run.id,
        true_positive_metric_stubs=[
            TruePositiveMetricStub(
                sample_id=image.sample_id,
                metrics={"iou": 0.75},
                gt_annotation_label_id=label.annotation_label_id,
            )
        ],
    )
    create_sample_metrics(
        session=db_session,
        run_id=other_run.id,
        sample_metrics=[SampleMetricStub(sample_id=image.sample_id, metrics={"score": 0.5})],
    )

    annotation_resolver.delete_annotation(db_session, gt_annotation.sample_id)

    deleted_run_annotation_metrics = (
        evaluation_annotation_metric_resolver.get_all_by_evaluation_run_id(
            session=db_session,
            evaluation_run_id=run.id,
        )
    )
    deleted_run_sample_metrics = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=run.id,
    )
    other_run_annotation_metrics = (
        evaluation_annotation_metric_resolver.get_all_by_evaluation_run_id(
            session=db_session,
            evaluation_run_id=other_run.id,
        )
    )
    other_run_sample_metrics = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=other_run.id,
    )

    assert deleted_run_annotation_metrics == []
    assert deleted_run_sample_metrics == []
    assert len(other_run_annotation_metrics) == 1
    assert len(other_run_sample_metrics) == 1
