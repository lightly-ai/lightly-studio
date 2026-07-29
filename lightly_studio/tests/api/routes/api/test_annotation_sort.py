"""Tests for sorting the annotations grid by a per-annotation evaluation metric."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_REQUEST,
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_OK,
)
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import collection_resolver
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)
from tests.resolvers.evaluation_sample_metric_resolver.helpers import (
    FalseNegativeMetricStub,
    FalsePositiveMetricStub,
    TruePositiveMetricStub,
    create_annotation_metrics,
    create_run,
)

METRIC_NAME = "iou"
# Exactly representable as a 32-bit float, so it round-trips through the value column.
MATCHED_VALUE = 0.75


@dataclass
class SortFixture:
    """One evaluation run holding every state the ordering has to distinguish.

    Attributes:
        run_id: The evaluation run.
        gt_collection_id: The ground-truth annotation source.
        pred_collection_id: The prediction annotation source.
        matched: Ground-truth annotation matched to a prediction, with a metric value.
        unmatched: Ground-truth annotation the run left unmatched (false negative).
        uncovered: Ground-truth annotation the run never covered.
        matched_pred: The prediction the matched ground truth pairs with.
        unmatched_pred: Prediction the run left unmatched (false positive).
    """

    run_id: UUID
    gt_collection_id: UUID
    pred_collection_id: UUID
    matched: UUID
    unmatched: UUID
    uncovered: UUID
    matched_pred: UUID
    unmatched_pred: UUID


@pytest.fixture
def sort_fixture(db_session: Session) -> SortFixture:
    root = create_collection(session=db_session)
    label = create_annotation_label(session=db_session, root_collection_id=root.collection_id)
    run = create_run(session=db_session, collection_id=root.collection_id)

    # Distinct file paths, because the parent file path is the leading tiebreaker.
    image_matched = create_image(
        session=db_session,
        collection_id=root.collection_id,
        file_path_abs="/path/to/a.png",
    )
    image_unmatched = create_image(
        session=db_session,
        collection_id=root.collection_id,
        file_path_abs="/path/to/b.png",
    )
    image_uncovered = create_image(
        session=db_session,
        collection_id=root.collection_id,
        file_path_abs="/path/to/c.png",
    )

    matched_stub, unmatched_stub, unmatched_pred_stub = create_annotation_metrics(
        session=db_session,
        run_id=run.id,
        pair_metric_stubs=[
            TruePositiveMetricStub(
                sample_id=image_matched.sample_id,
                metrics={METRIC_NAME: MATCHED_VALUE},
                gt_annotation_label_id=label.annotation_label_id,
            ),
            FalseNegativeMetricStub(
                sample_id=image_unmatched.sample_id,
                gt_annotation_label_id=label.annotation_label_id,
            ),
            FalsePositiveMetricStub(
                sample_id=image_unmatched.sample_id,
                pred_annotation_label_id=label.annotation_label_id,
            ),
        ],
    )

    gt_collection = collection_resolver.get_by_id(
        session=db_session, collection_id=run.gt_annotation_collection_id
    )
    assert gt_collection is not None
    uncovered = create_annotation(
        session=db_session,
        collection_id=root.collection_id,
        sample_id=image_uncovered.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_collection_name=gt_collection.name,
    )

    assert matched_stub.gt_annotation_id is not None
    assert matched_stub.pred_annotation_id is not None
    assert unmatched_stub.gt_annotation_id is not None
    assert unmatched_pred_stub.pred_annotation_id is not None
    return SortFixture(
        run_id=run.id,
        gt_collection_id=run.gt_annotation_collection_id,
        pred_collection_id=run.pred_annotation_collection_id,
        matched=matched_stub.gt_annotation_id,
        unmatched=unmatched_stub.gt_annotation_id,
        uncovered=uncovered.sample_id,
        matched_pred=matched_stub.pred_annotation_id,
        unmatched_pred=unmatched_pred_stub.pred_annotation_id,
    )


def test_read_annotations_with_payload__sort_ascending(
    test_client: TestClient,
    sort_fixture: SortFixture,
) -> None:
    annotations = _sorted_annotations(
        test_client=test_client,
        collection_id=sort_fixture.gt_collection_id,
        run_id=sort_fixture.run_id,
        direction="asc",
    )

    # Unmatched orders as 0.0 ahead of the matched value; uncovered orders last.
    assert _sample_ids(annotations) == [
        sort_fixture.unmatched,
        sort_fixture.matched,
        sort_fixture.uncovered,
    ]
    assert _sort_values(annotations) == [0.0, MATCHED_VALUE, None]


def test_read_annotations_with_payload__sort_descending(
    test_client: TestClient,
    sort_fixture: SortFixture,
) -> None:
    annotations = _sorted_annotations(
        test_client=test_client,
        collection_id=sort_fixture.gt_collection_id,
        run_id=sort_fixture.run_id,
        direction="desc",
    )

    # Uncovered stays last in both directions.
    assert _sample_ids(annotations) == [
        sort_fixture.matched,
        sort_fixture.unmatched,
        sort_fixture.uncovered,
    ]
    assert _sort_values(annotations) == [MATCHED_VALUE, 0.0, None]


def test_read_annotations_with_payload__sort_on_prediction_source(
    test_client: TestClient,
    sort_fixture: SortFixture,
) -> None:
    annotations = _sorted_annotations(
        test_client=test_client,
        collection_id=sort_fixture.pred_collection_id,
        run_id=sort_fixture.run_id,
        direction="desc",
    )

    # The same request body resolves against the prediction side of the pairing.
    assert _sample_ids(annotations) == [
        sort_fixture.matched_pred,
        sort_fixture.unmatched_pred,
    ]
    assert _sort_values(annotations) == [MATCHED_VALUE, 0.0]


def test_read_annotations_with_payload__sort_by_unknown_run(
    test_client: TestClient,
    sort_fixture: SortFixture,
) -> None:
    response = _post_sorted(
        test_client=test_client,
        collection_id=sort_fixture.gt_collection_id,
        run_id=uuid4(),
        direction="asc",
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND


def test_read_annotations_with_payload__sort_by_run_of_other_source(
    test_client: TestClient,
    db_session: Session,
    sort_fixture: SortFixture,
) -> None:
    gt_collection = collection_resolver.get_by_id(
        session=db_session, collection_id=sort_fixture.gt_collection_id
    )
    assert gt_collection is not None
    assert gt_collection.parent_collection_id is not None
    unrelated_source = create_collection(
        session=db_session,
        parent_collection_id=gt_collection.parent_collection_id,
        sample_type=SampleType.ANNOTATION,
    )

    response = _post_sorted(
        test_client=test_client,
        collection_id=unrelated_source.collection_id,
        run_id=sort_fixture.run_id,
        direction="asc",
    )

    assert response.status_code == HTTP_STATUS_BAD_REQUEST


def test_read_annotations_with_payload__sort_by_metric_without_rows(
    test_client: TestClient,
    db_session: Session,
) -> None:
    root = create_collection(session=db_session)
    label = create_annotation_label(session=db_session, root_collection_id=root.collection_id)
    run = create_run(session=db_session, collection_id=root.collection_id)
    image = create_image(session=db_session, collection_id=root.collection_id)
    create_annotation_metrics(
        session=db_session,
        run_id=run.id,
        pair_metric_stubs=[
            TruePositiveMetricStub(
                sample_id=image.sample_id,
                metrics={METRIC_NAME: MATCHED_VALUE},
                gt_annotation_label_id=label.annotation_label_id,
            ),
        ],
    )

    annotations = _sorted_annotations(
        test_client=test_client,
        collection_id=run.gt_annotation_collection_id,
        run_id=run.id,
        direction="asc",
        metric_name="disagreement",
    )

    assert len(annotations) == 1
    assert _sort_values(annotations) == [None]


def test_read_annotations_with_payload__sort_composes_with_label_filter(
    test_client: TestClient,
    db_session: Session,
    sort_fixture: SortFixture,
) -> None:
    other_label = create_annotation_label(
        session=db_session,
        root_collection_id=_root_collection_id(db_session=db_session, fixture=sort_fixture),
        label_name="airplane",
    )

    response = test_client.post(
        f"/api/collections/{sort_fixture.gt_collection_id}/annotations/payload",
        json={
            "pagination": {"offset": 0, "limit": 100},
            "annotation_label_ids": [str(other_label.annotation_label_id)],
            "sort_by": {
                "source": "annotation_evaluation_metric",
                "evaluation_run_id": str(sort_fixture.run_id),
                "metric_name": METRIC_NAME,
                "direction": "asc",
            },
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json()["total_count"] == 0


def test_read_annotations_with_payload__sort_does_not_multiply_rows(
    test_client: TestClient,
    db_session: Session,
) -> None:
    root = create_collection(session=db_session)
    label = create_annotation_label(session=db_session, root_collection_id=root.collection_id)
    run = create_run(session=db_session, collection_id=root.collection_id)
    image = create_image(session=db_session, collection_id=root.collection_id)
    # Two metrics on one annotation: the join must still yield a single grid row.
    create_annotation_metrics(
        session=db_session,
        run_id=run.id,
        pair_metric_stubs=[
            TruePositiveMetricStub(
                sample_id=image.sample_id,
                metrics={METRIC_NAME: MATCHED_VALUE, "disagreement": 0.25},
                gt_annotation_label_id=label.annotation_label_id,
            ),
        ],
    )

    response = _post_sorted(
        test_client=test_client,
        collection_id=run.gt_annotation_collection_id,
        run_id=run.id,
        direction="asc",
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json()["total_count"] == 1
    assert _sort_values(response.json()["data"]) == [MATCHED_VALUE]


def _root_collection_id(db_session: Session, fixture: SortFixture) -> UUID:
    gt_collection = collection_resolver.get_by_id(
        session=db_session, collection_id=fixture.gt_collection_id
    )
    assert gt_collection is not None
    assert gt_collection.parent_collection_id is not None
    return gt_collection.parent_collection_id


def _post_sorted(
    test_client: TestClient,
    collection_id: UUID,
    run_id: UUID,
    direction: str,
    metric_name: str = METRIC_NAME,
) -> Response:
    return test_client.post(
        f"/api/collections/{collection_id}/annotations/payload",
        json={
            "pagination": {"offset": 0, "limit": 100},
            "sort_by": {
                "source": "annotation_evaluation_metric",
                "evaluation_run_id": str(run_id),
                "metric_name": metric_name,
                "direction": direction,
            },
        },
    )


def _sorted_annotations(
    test_client: TestClient,
    collection_id: UUID,
    run_id: UUID,
    direction: str,
    metric_name: str = METRIC_NAME,
) -> list[Any]:
    response = _post_sorted(
        test_client=test_client,
        collection_id=collection_id,
        run_id=run_id,
        direction=direction,
        metric_name=metric_name,
    )
    assert response.status_code == HTTP_STATUS_OK
    data: list[Any] = response.json()["data"]
    return data


def _sample_ids(annotations: list[Any]) -> list[UUID]:
    return [UUID(annotation["annotation"]["sample_id"]) for annotation in annotations]


def _sort_values(annotations: list[Any]) -> list[float | None]:
    return [annotation["sort_value"] for annotation in annotations]
