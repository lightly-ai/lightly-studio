"""Tests that the annotations grid and the adjacency walk agree on the ordering."""

from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from lightly_studio.models.collection import SampleType
from tests import helpers_resolvers


def test_annotation_ordering__grid_page_matches_adjacency_walk(
    db_session: Session,
    test_client: TestClient,
) -> None:
    collection = helpers_resolvers.create_collection(
        session=db_session, sample_type=SampleType.IMAGE
    )
    collection_id = collection.collection_id

    label = helpers_resolvers.create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="dog",
    )

    # Paths are created out of order so that ordering by file path is observable.
    images = [
        helpers_resolvers.create_image(
            session=db_session,
            collection_id=collection_id,
            file_path_abs=file_path_abs,
        )
        for file_path_abs in ["/images/c.png", "/images/a.png", "/images/b.png"]
    ]

    # Two annotations per image so the created-at and annotation-id tiebreakers matter.
    annotations = helpers_resolvers.create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            helpers_resolvers.AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
            )
            for image in images
            for _ in range(2)
        ],
    )
    annotation_collection_id = annotations[0].sample.collection_id

    grid_response = test_client.post(
        f"/api/collections/{annotation_collection_id}/annotations/payload",
        json={"pagination": {"cursor": 0, "limit": len(annotations)}},
    )
    assert grid_response.status_code == HTTP_STATUS_OK
    grid_sample_ids = [
        UUID(entry["annotation"]["sample_id"]) for entry in grid_response.json()["data"]
    ]
    assert len(grid_sample_ids) == len(annotations)

    walked_sample_ids = _walk_adjacents(
        test_client=test_client,
        collection_id=annotation_collection_id,
        start_sample_id=grid_sample_ids[0],
    )

    assert walked_sample_ids == grid_sample_ids


def _walk_adjacents(
    test_client: TestClient,
    collection_id: UUID,
    start_sample_id: UUID,
) -> list[UUID]:
    """Follow the adjacency endpoint's next pointers, starting at the given annotation."""
    sample_ids: list[UUID] = []
    sample_id: UUID | None = start_sample_id
    while sample_id is not None:
        response = test_client.post(
            f"/api/samples/{sample_id}/adjacents",
            json={
                "sample_type": SampleType.ANNOTATION.value,
                "collection_id": str(collection_id),
                "filters": {
                    "filter_type": "annotations",
                    "collection_ids": [str(collection_id)],
                },
            },
        )
        assert response.status_code == HTTP_STATUS_OK
        data = response.json()
        assert data is not None
        assert UUID(data["sample_id"]) == sample_id
        assert data["current_sample_position"] == len(sample_ids) + 1

        sample_ids.append(sample_id)
        next_sample_id = data["next_sample_id"]
        sample_id = UUID(next_sample_id) if next_sample_id is not None else None

    return sample_ids
