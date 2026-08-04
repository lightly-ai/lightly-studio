from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session, col, select

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_CREATED,
    HTTP_STATUS_UNPROCESSABLE_ENTITY,
)
from lightly_studio.models.sample import SampleTagLinkTable
from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import ImageStub, create_collection, create_image, create_images


def test_create_split__no_filter_splits_whole_collection(
    db_session: Session, test_client: TestClient
) -> None:
    collection_id = create_collection(session=db_session).collection_id
    create_images(
        db_session=db_session,
        collection_id=collection_id,
        images=[ImageStub(path=f"s{i}.png") for i in range(10)],
    )

    response = test_client.post(
        f"/api/collections/{collection_id}/splits",
        json={"sizes": {"train": 80, "val": 10, "test": 10}, "seed": 42},
    )

    assert response.status_code == HTTP_STATUS_CREATED
    body = response.json()
    assert body["seed"] == 42
    counts = {split["name"]: split["count"] for split in body["splits"]}
    assert counts == {"train": 8, "val": 1, "test": 1}


def test_create_split__with_filter_splits_only_matching(
    db_session: Session, test_client: TestClient
) -> None:
    collection_id = create_collection(session=db_session).collection_id
    create_image(
        session=db_session, collection_id=collection_id, file_path_abs="wide.png", width=1920
    )
    create_image(
        session=db_session, collection_id=collection_id, file_path_abs="narrow.png", width=10
    )

    response = test_client.post(
        f"/api/collections/{collection_id}/splits",
        json={
            "sizes": {"train": 50, "val": 50},
            "filter": {"filter_type": "image", "width": {"min": 100}},
            "seed": 1,
        },
    )

    assert response.status_code == HTTP_STATUS_CREATED
    counts = {split["name"]: split["count"] for split in response.json()["splits"]}
    assert sum(counts.values()) == 1


def test_create_split__split_tags_are_created_and_linked(
    db_session: Session, test_client: TestClient
) -> None:
    collection_id = create_collection(session=db_session).collection_id
    images = create_images(
        db_session=db_session,
        collection_id=collection_id,
        images=[ImageStub(path=f"s{i}.png") for i in range(4)],
    )

    response = test_client.post(
        f"/api/collections/{collection_id}/splits",
        json={"sizes": {"train": 50, "val": 50}, "seed": 3},
    )

    assert response.status_code == HTTP_STATUS_CREATED
    train_tag = tag_resolver.get_by_name(
        session=db_session, tag_name="train", collection_id=collection_id
    )
    val_tag = tag_resolver.get_by_name(
        session=db_session, tag_name="val", collection_id=collection_id
    )
    assert train_tag is not None
    assert val_tag is not None
    all_split_ids = _tagged_sample_ids(
        session=db_session, tag_id=train_tag.tag_id
    ) | _tagged_sample_ids(session=db_session, tag_id=val_tag.tag_id)
    assert all_split_ids == {image.sample_id for image in images}


def test_create_split__invalid_sizes_returns_422(
    db_session: Session, test_client: TestClient
) -> None:
    collection_id = create_collection(session=db_session).collection_id
    create_image(session=db_session, collection_id=collection_id, file_path_abs="s.png")

    response = test_client.post(
        f"/api/collections/{collection_id}/splits",
        json={"sizes": {"train": 80, "val": 10}},
    )

    assert response.status_code == HTTP_STATUS_UNPROCESSABLE_ENTITY


def _tagged_sample_ids(session: Session, tag_id: UUID) -> set[UUID]:
    linked = session.exec(
        select(SampleTagLinkTable.sample_id).where(col(SampleTagLinkTable.tag_id) == tag_id)
    ).all()
    return {sample_id for sample_id in linked if sample_id is not None}
