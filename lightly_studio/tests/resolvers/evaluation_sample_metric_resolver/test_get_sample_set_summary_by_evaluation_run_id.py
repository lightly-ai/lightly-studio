from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import evaluation_sample_metric_resolver, tag_resolver
from tests.helpers_resolvers import create_collection, create_image, create_tag
from tests.resolvers.evaluation_sample_metric_resolver import (
    helpers as evaluation_sample_metric_helpers,
)

THREE_METRICS = {"tp": 1.0, "fp": 0.0, "fn": 0.0}


def test_get_sample_set_summary_by_evaluation_run_id(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    run = evaluation_sample_metric_helpers.create_run(
        session=db_session, collection_id=dataset.collection_id
    )
    sample_ids = [
        create_image(session=db_session, collection_id=dataset.collection_id).sample_id,
        create_image(session=db_session, collection_id=dataset.collection_id).sample_id,
    ]
    _create_metrics(session=db_session, run_id=run.id, sample_ids=sample_ids)

    summary = evaluation_sample_metric_resolver.get_sample_set_summary_by_evaluation_run_id(
        session=db_session, evaluation_run_id=run.id
    )

    # Two images with three metrics each count as two samples.
    assert summary.sample_count == 2


def test_get_sample_set_summary_by_evaluation_run_id__same_samples_same_hash(
    db_session: Session,
) -> None:
    dataset = create_collection(session=db_session)
    sample_ids = [
        create_image(session=db_session, collection_id=dataset.collection_id).sample_id,
        create_image(session=db_session, collection_id=dataset.collection_id).sample_id,
    ]
    run_1 = evaluation_sample_metric_helpers.create_run(
        session=db_session, collection_id=dataset.collection_id, name="run_1"
    )
    run_2 = evaluation_sample_metric_helpers.create_run(
        session=db_session, collection_id=dataset.collection_id, name="run_2"
    )
    _create_metrics(session=db_session, run_id=run_1.id, sample_ids=sample_ids)
    _create_metrics(session=db_session, run_id=run_2.id, sample_ids=list(reversed(sample_ids)))

    summary_1 = evaluation_sample_metric_resolver.get_sample_set_summary_by_evaluation_run_id(
        session=db_session, evaluation_run_id=run_1.id
    )
    summary_2 = evaluation_sample_metric_resolver.get_sample_set_summary_by_evaluation_run_id(
        session=db_session, evaluation_run_id=run_2.id
    )

    assert summary_1.sample_set_hash == summary_2.sample_set_hash


def test_get_sample_set_summary_by_evaluation_run_id__different_samples_different_hash(
    db_session: Session,
) -> None:
    dataset = create_collection(session=db_session)
    sample_ids = [
        create_image(session=db_session, collection_id=dataset.collection_id).sample_id,
        create_image(session=db_session, collection_id=dataset.collection_id).sample_id,
    ]
    run_1 = evaluation_sample_metric_helpers.create_run(
        session=db_session, collection_id=dataset.collection_id, name="run_1"
    )
    run_2 = evaluation_sample_metric_helpers.create_run(
        session=db_session, collection_id=dataset.collection_id, name="run_2"
    )
    _create_metrics(session=db_session, run_id=run_1.id, sample_ids=sample_ids)
    _create_metrics(session=db_session, run_id=run_2.id, sample_ids=sample_ids[:1])

    summary_1 = evaluation_sample_metric_resolver.get_sample_set_summary_by_evaluation_run_id(
        session=db_session, evaluation_run_id=run_1.id
    )
    summary_2 = evaluation_sample_metric_resolver.get_sample_set_summary_by_evaluation_run_id(
        session=db_session, evaluation_run_id=run_2.id
    )

    assert summary_1.sample_set_hash != summary_2.sample_set_hash


def test_get_sample_set_summary_by_evaluation_run_id__no_metrics(db_session: Session) -> None:
    run = evaluation_sample_metric_helpers.create_run(session=db_session)

    summary = evaluation_sample_metric_resolver.get_sample_set_summary_by_evaluation_run_id(
        session=db_session, evaluation_run_id=run.id
    )

    assert summary.sample_count == 0


def test_get_sample_set_summary_by_evaluation_run_id__within_tag(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    run = evaluation_sample_metric_helpers.create_run(
        session=db_session, collection_id=dataset.collection_id
    )
    sample_ids = [
        create_image(
            session=db_session,
            collection_id=dataset.collection_id,
            file_path_abs=f"/path/to/{index}.png",
        ).sample_id
        for index in range(3)
    ]
    _create_metrics(session=db_session, run_id=run.id, sample_ids=sample_ids)
    tag = create_tag(session=db_session, collection_id=dataset.collection_id)
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tag.tag_id, sample_ids=sample_ids[:2]
    )

    summary = evaluation_sample_metric_resolver.get_sample_set_summary_by_evaluation_run_id(
        session=db_session, evaluation_run_id=run.id, tag_id=tag.tag_id
    )

    assert summary.sample_count == 2


def _create_metrics(session: Session, run_id: UUID, sample_ids: list[UUID]) -> None:
    evaluation_sample_metric_helpers.create_sample_metrics(
        session=session,
        run_id=run_id,
        sample_metrics=[
            evaluation_sample_metric_helpers.SampleMetricStub(
                sample_id=sample_id, metrics=THREE_METRICS
            )
            for sample_id in sample_ids
        ],
    )
