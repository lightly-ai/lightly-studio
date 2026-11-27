from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.evaluation_run import EvaluationRunCreate, EvaluationTaskType
from lightly_studio.resolvers import evaluation_run_resolver
from tests.helpers_resolvers import create_collection


def test_get_names_by_collection_id(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    gt, pred, other = (
        create_collection(
            session=db_session,
            collection_name=name,
            sample_type=SampleType.ANNOTATION,
            parent_collection_id=dataset.collection_id,
        )
        for name in ("ground_truth", "predictions", "other")
    )
    for name, gt_id, pred_id in (
        ("run_b", gt.collection_id, pred.collection_id),
        ("run_a", pred.collection_id, gt.collection_id),
        ("run_c", other.collection_id, gt.collection_id),
    ):
        evaluation_run_resolver.create(
            session=db_session,
            evaluation_run_input=EvaluationRunCreate(
                name=name,
                gt_annotation_collection_id=gt_id,
                pred_annotation_collection_id=pred_id,
                dataset_id=dataset.dataset_id,
                task_type=EvaluationTaskType.OBJECT_DETECTION,
            ),
        )

    names = evaluation_run_resolver.get_names_by_collection_id(
        session=db_session, collection_id=pred.collection_id
    )

    assert names == ["run_a", "run_b"]
