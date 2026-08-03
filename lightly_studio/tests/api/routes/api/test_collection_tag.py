from __future__ import annotations

import uuid
from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session, col, select

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_CREATED,
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_OK,
)
from lightly_studio.models.collection import SampleType
from lightly_studio.models.sample import SampleTagLinkTable
from lightly_studio.resolvers import collection_resolver
from tests.helpers_resolvers import (
    ImageStub,
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
    create_images,
    create_tag,
)


def test_add_samples_by_filter__image_empty_filter_tags_whole_collection(
    db_session: Session, test_client: TestClient
) -> None:
    collection_id = create_collection(session=db_session).collection_id
    tag = create_tag(session=db_session, collection_id=collection_id, kind="sample")
    images = create_images(
        db_session=db_session,
        collection_id=collection_id,
        images=[ImageStub(path="s0.png"), ImageStub(path="s1.png")],
    )

    response = test_client.post(
        f"/api/collections/{collection_id}/tags/{tag.tag_id}/add/samples_by_filter",
        json={"filter": {"filter_type": "image"}},
    )

    assert response.status_code == HTTP_STATUS_CREATED
    assert _tagged_sample_ids(session=db_session, tag_id=tag.tag_id) == {
        image.sample_id for image in images
    }


def test_add_samples_by_filter__image_subset_filter_tags_only_subset(
    db_session: Session, test_client: TestClient
) -> None:
    collection_id = create_collection(session=db_session).collection_id
    tag = create_tag(session=db_session, collection_id=collection_id, kind="sample")
    wide = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="wide.png", width=1920
    )
    create_image(
        session=db_session, collection_id=collection_id, file_path_abs="narrow.png", width=10
    )

    response = test_client.post(
        f"/api/collections/{collection_id}/tags/{tag.tag_id}/add/samples_by_filter",
        json={"filter": {"filter_type": "image", "width": {"min": 100}}},
    )

    assert response.status_code == HTTP_STATUS_CREATED
    assert _tagged_sample_ids(session=db_session, tag_id=tag.tag_id) == {wide.sample_id}


def test_add_samples_by_filter__idempotent_on_rerun(
    db_session: Session, test_client: TestClient
) -> None:
    collection_id = create_collection(session=db_session).collection_id
    tag = create_tag(session=db_session, collection_id=collection_id, kind="sample")
    image = create_image(session=db_session, collection_id=collection_id, file_path_abs="s.png")
    body = {"filter": {"filter_type": "image"}}

    url = f"/api/collections/{collection_id}/tags/{tag.tag_id}/add/samples_by_filter"
    first = test_client.post(url, json=body)
    second = test_client.post(url, json=body)

    assert first.status_code == HTTP_STATUS_CREATED
    assert second.status_code == HTTP_STATUS_CREATED
    # Re-running adds no duplicate link.
    assert _tagged_sample_ids(session=db_session, tag_id=tag.tag_id) == {image.sample_id}


def test_add_samples_by_filter__annotation_grid(
    db_session: Session, test_client: TestClient
) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    tag = create_tag(session=db_session, collection_id=annotation_collection_id, kind="annotation")

    response = test_client.post(
        f"/api/collections/{annotation_collection_id}/tags/{tag.tag_id}/add/samples_by_filter",
        json={"filter": {"filter_type": "annotations"}},
    )

    assert response.status_code == HTTP_STATUS_CREATED
    assert _tagged_sample_ids(session=db_session, tag_id=tag.tag_id) == {annotation.sample_id}


def test_add_samples_by_filter__unknown_tag_returns_404(
    db_session: Session, test_client: TestClient
) -> None:
    collection_id = create_collection(session=db_session).collection_id

    response = test_client.post(
        f"/api/collections/{collection_id}/tags/{uuid.uuid4()}/add/samples_by_filter",
        json={"filter": {"filter_type": "image"}},
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND


def test_add_samples_by_filter__wrong_collection_returns_404(
    db_session: Session, test_client: TestClient
) -> None:
    collection_id = create_collection(session=db_session).collection_id
    tag = create_tag(session=db_session, collection_id=collection_id, kind="sample")

    # Tag exists, but not in the collection on the path.
    response = test_client.post(
        f"/api/collections/{uuid.uuid4()}/tags/{tag.tag_id}/add/samples_by_filter",
        json={"filter": {"filter_type": "image"}},
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND


def test_remove_sample_ids_from_tag_id(db_session: Session, test_client: TestClient) -> None:
    collection_id = create_collection(session=db_session).collection_id
    tag = create_tag(session=db_session, collection_id=collection_id, kind="sample")
    kept, removed = create_images(
        db_session=db_session,
        collection_id=collection_id,
        images=[ImageStub(path="kept.png"), ImageStub(path="removed.png")],
    )
    test_client.post(
        f"/api/collections/{collection_id}/tags/{tag.tag_id}/add/samples",
        json={"sample_ids": [str(kept.sample_id), str(removed.sample_id)]},
    )

    response = test_client.request(
        "DELETE",
        f"/api/collections/{collection_id}/tags/{tag.tag_id}/remove/samples",
        json={"sample_ids": [str(removed.sample_id)]},
    )

    assert response.status_code == HTTP_STATUS_OK
    assert _tagged_sample_ids(session=db_session, tag_id=tag.tag_id) == {kept.sample_id}


def test_remove_sample_ids_from_tag_id__unknown_tag_returns_404(
    db_session: Session, test_client: TestClient
) -> None:
    collection_id = create_collection(session=db_session).collection_id

    response = test_client.request(
        "DELETE",
        f"/api/collections/{collection_id}/tags/{uuid.uuid4()}/remove/samples",
        json={"sample_ids": []},
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND


def test_remove_sample_ids_from_tag_id__wrong_collection_returns_404(
    db_session: Session, test_client: TestClient
) -> None:
    collection_id = create_collection(session=db_session).collection_id
    tag = create_tag(session=db_session, collection_id=collection_id, kind="sample")
    image = create_image(session=db_session, collection_id=collection_id, file_path_abs="s.png")
    test_client.post(
        f"/api/collections/{collection_id}/tags/{tag.tag_id}/add/samples",
        json={"sample_ids": [str(image.sample_id)]},
    )

    # Tag exists, but not in the collection on the path.
    response = test_client.request(
        "DELETE",
        f"/api/collections/{uuid.uuid4()}/tags/{tag.tag_id}/remove/samples",
        json={"sample_ids": [str(image.sample_id)]},
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND
    # The link must survive a request scoped to the wrong collection.
    assert _tagged_sample_ids(session=db_session, tag_id=tag.tag_id) == {image.sample_id}


def _tagged_sample_ids(session: Session, tag_id: UUID) -> set[UUID]:
    """Read the sample ids currently linked to ``tag_id`` straight from the link table."""
    linked = session.exec(
        select(SampleTagLinkTable.sample_id).where(col(SampleTagLinkTable.tag_id) == tag_id)
    ).all()
    return {sample_id for sample_id in linked if sample_id is not None}
