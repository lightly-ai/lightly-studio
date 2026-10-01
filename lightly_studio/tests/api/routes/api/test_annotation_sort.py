"""Tests for wiring the annotation evaluation metric sort into the annotations endpoint.

The order-by class (tests/core/dataset_query/test_order_by.py), the side resolution
(tests/resolvers/annotations/test_annotation_metric_sort.py) and the ordering semantics
(tests/resolvers/annotations/test_get_all_with_payload_metric_sort.py) are covered elsewhere. This
file only proves the endpoint wires them together.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_REQUEST,
    HTTP_STATUS_OK,
)
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import collection_resolver
from tests.helpers_resolvers import create_annotation_label, create_collection, create_image
from tests.resolvers.evaluation_sample_metric_resolver.helpers import (
    FalseNegativeMetricStub,
    TruePositiveMetricStub,
    create_annotation_metrics,
    create_run,
)

METRIC_NAME = "iou"
MATCHED_VALUE = 0.75


@dataclass
class _RunWithMatchedAndUnmatchedAnnotations:
    """One evaluation run with a matched pair and an unmatched ground truth annotation."""

    run_id: UUID
    gt_collection_id: UUID
    matched_gt: UUID
    unmatched_gt: UUID


def test_read_annotations_with_payload__sorts_by_annotation_evaluation_metric(
    test_client: TestClient,
    db_session: Session,
) -> None:
    fixture = _create_run_with_matched_and_unmatched_annotations(session=db_session)

    response = test_client.post(
        f"/api/collections/{fixture.gt_collection_id}/annotations/payload",
        json={
            "pagination": {"offset": 0, "limit": 100},
            "sort_by": {
                "source": "annotation_evaluation_metric",
                "evaluation_run_id": str(fixture.run_id),
                "metric_name": METRIC_NAME,
                "direction": "asc",
            },
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    # Unmatched orders as 0.0, ahead of the matched value.
    assert [UUID(a["annotation"]["sample_id"]) for a in response.json()["data"]] == [
        fixture.unmatched_gt,
        fixture.matched_gt,
    ]


def test_read_annotations_with_payload__sort_by_unknown_run_returns_400(
    test_client: TestClient,
    db_session: Session,
) -> None:
    fixture = _create_run_with_matched_and_unmatched_annotations(session=db_session)

    response = test_client.post(
        f"/api/collections/{fixture.gt_collection_id}/annotations/payload",
        json={
            "pagination": {"offset": 0, "limit": 100},
            "sort_by": {
                "source": "annotation_evaluation_metric",
                "evaluation_run_id": str(uuid4()),
                "metric_name": METRIC_NAME,
                "direction": "asc",
            },
        },
    )

    assert response.status_code == HTTP_STATUS_BAD_REQUEST


def test_read_annotations_with_payload__sort_by_run_of_other_source_returns_400(
    test_client: TestClient,
    db_session: Session,
) -> None:
    fixture = _create_run_with_matched_and_unmatched_annotations(session=db_session)
    gt_collection = collection_resolver.get_by_id(
        session=db_session, collection_id=fixture.gt_collection_id
    )
    assert gt_collection is not None
    unrelated_source = create_collection(
        session=db_session,
        parent_collection_id=gt_collection.parent_collection_id,
        sample_type=SampleType.ANNOTATION,
    )

    response = test_client.post(
        f"/api/collections/{unrelated_source.collection_id}/annotations/payload",
        json={
            "pagination": {"offset": 0, "limit": 100},
            "sort_by": {
                "source": "annotation_evaluation_metric",
                "evaluation_run_id": str(fixture.run_id),
                "metric_name": METRIC_NAME,
                "direction": "asc",
            },
        },
    )

    assert response.status_code == HTTP_STATUS_BAD_REQUEST


def _create_run_with_matched_and_unmatched_annotations(
    session: Session,
) -> _RunWithMatchedAndUnmatchedAnnotations:
    root = create_collection(session=session)
    label = create_annotation_label(session=session, root_collection_id=root.collection_id)
    run = create_run(session=session, collection_id=root.collection_id)
    image_matched = create_image(
        session=session, collection_id=root.collection_id, file_path_abs="/a.png"
    )
    image_unmatched = create_image(
        session=session, collection_id=root.collection_id, file_path_abs="/b.png"
    )

    matched_stub, unmatched_gt_stub = create_annotation_metrics(
        session=session,
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
        ],
    )

    assert matched_stub.gt_annotation_id is not None
    assert unmatched_gt_stub.gt_annotation_id is not None
    return _RunWithMatchedAndUnmatchedAnnotations(
        run_id=run.id,
        gt_collection_id=run.gt_annotation_collection_id,
        matched_gt=matched_stub.gt_annotation_id,
        unmatched_gt=unmatched_gt_stub.gt_annotation_id,
    )
