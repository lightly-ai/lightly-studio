from __future__ import annotations

import uuid

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.evaluation_run import EvaluationRunCreate, EvaluationTaskType
from lightly_studio.resolvers import evaluation_run_resolver
from tests.helpers_resolvers import create_collection


def test_list_views_by_dataset_id(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    gt = create_collection(
        session=db_session,
        collection_name="gt",
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=dataset.collection_id,
    )
    pred = create_collection(
        session=db_session,
        collection_name="pred",
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=dataset.collection_id,
    )
    run_1 = evaluation_run_resolver.create(
        session=db_session,
        evaluation_run_input=EvaluationRunCreate(
            name="run_1",
            gt_annotation_collection_id=gt.collection_id,
            pred_annotation_collection_id=pred.collection_id,
            dataset_id=dataset.dataset_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
            config_json={"iou_threshold": 0.5, "classwise": True},
        ),
    )
    run_2 = evaluation_run_resolver.create(
        session=db_session,
        evaluation_run_input=EvaluationRunCreate(
            name="run_2",
            gt_annotation_collection_id=gt.collection_id,
            pred_annotation_collection_id=pred.collection_id,
            dataset_id=dataset.dataset_id,
            task_type=EvaluationTaskType.CLASSIFICATION,
        ),
    )

    views = evaluation_run_resolver.list_views_by_dataset_id(
        session=db_session, dataset_id=dataset.dataset_id
    )

    # Newest first, ground-truth and prediction collection IDs resolved to names.
    assert [view.id for view in views] == [run_2.id, run_1.id]
    view_1 = next(view for view in views if view.id == run_1.id)
    assert view_1.name == "run_1"
    assert view_1.gt_annotation_source == "gt"
    assert view_1.pred_annotation_source == "pred"
    assert view_1.evaluation_run_configuration == {"iou_threshold": 0.5, "classwise": True}


def test_list_views_by_dataset_id__returns_empty_for_unknown_dataset(db_session: Session) -> None:
    views = evaluation_run_resolver.list_views_by_dataset_id(
        session=db_session, dataset_id=uuid.uuid4()
    )

    assert views == []
