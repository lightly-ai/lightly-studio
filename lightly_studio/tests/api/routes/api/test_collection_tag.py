from __future__ import annotations

import uuid
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlmodel import Session, col, select

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_CREATED,
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_UNPROCESSABLE_ENTITY,
)
from lightly_studio.models.collection import SampleType
from lightly_studio.models.sample import SampleTagLinkTable
from lightly_studio.models.two_dim_embedding import TwoDimEmbeddingTable
from lightly_studio.resolvers import collection_resolver, sample_embedding_resolver, tag_resolver
from tests.helpers_resolvers import (
    ImageStub,
    create_annotation,
    create_annotation_label,
    create_collection,
    create_embedding_model,
    create_image,
    create_images,
    create_sample_embedding,
    create_samples_with_embeddings,
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


def test_add_samples_by_filter__image_filter_with_embedding_region_tags_only_region_samples(
    db_session: Session, test_client: TestClient
) -> None:
    """Tagging by filter with an embedding region only tags samples inside the region."""
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    tag = create_tag(session=db_session, collection_id=collection_id, kind="sample")
    embedding_model = create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_dimension=3,
        set_as_default=True,
    )
    # Two samples inside the square region [0,10]x[0,10], one far outside.
    images = create_samples_with_embeddings(
        session=db_session,
        collection_id=collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
        images_and_embeddings=[
            (ImageStub(path="inside_a.png"), [0.1, 0.2, 0.3]),
            (ImageStub(path="inside_b.png"), [1.1, 0.2, 0.3]),
            (ImageStub(path="outside.png"), [2.1, 0.2, 0.3]),
        ],
    )
    inside_a = images[0]
    inside_b = images[1]
    outside = images[2]
    # Seed the 2D embedding cache with known coordinates.
    cache_key, cached_sample_ids = sample_embedding_resolver.get_hash_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )
    coordinates_by_sample = {
        inside_a.sample_id: (1.0, 1.0),
        inside_b.sample_id: (5.0, 5.0),
        outside.sample_id: (100.0, 100.0),
    }
    db_session.add(
        TwoDimEmbeddingTable(
            hash=cache_key,
            x=[coordinates_by_sample[sid][0] for sid in cached_sample_ids],
            y=[coordinates_by_sample[sid][1] for sid in cached_sample_ids],
        )
    )
    db_session.commit()

    response = test_client.post(
        f"/api/collections/{collection_id}/tags/{tag.tag_id}/add/samples_by_filter",
        json={
            "filter": {
                "filter_type": "image",
                "sample_filter": {
                    "embedding_region": {
                        "polygon": [
                            {"x": 0.0, "y": 0.0},
                            {"x": 10.0, "y": 0.0},
                            {"x": 10.0, "y": 10.0},
                            {"x": 0.0, "y": 10.0},
                        ]
                    }
                },
            }
        },
    )

    assert response.status_code == HTTP_STATUS_CREATED
    assert _tagged_sample_ids(session=db_session, tag_id=tag.tag_id) == {
        inside_a.sample_id,
        inside_b.sample_id,
    }


def test_add_samples_by_filter__annotations_filter_with_embedding_region_tags_only_region_samples(
    db_session: Session, test_client: TestClient
) -> None:
    """AnnotationsFilter with embedding region only tags samples inside the region."""
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    inside_a = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    inside_b = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    outside = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    tag = create_tag(session=db_session, collection_id=annotation_collection_id, kind="annotation")
    embedding_model = create_embedding_model(
        session=db_session,
        collection_id=annotation_collection_id,
        embedding_dimension=3,
        set_as_default=True,
    )
    create_sample_embedding(
        session=db_session,
        sample_id=inside_a.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[0.1, 0.2, 0.3],
    )
    create_sample_embedding(
        session=db_session,
        sample_id=inside_b.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[1.1, 0.2, 0.3],
    )
    create_sample_embedding(
        session=db_session,
        sample_id=outside.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[2.1, 0.2, 0.3],
    )
    # Seed the 2D embedding cache with known coordinates.
    cache_key, cached_sample_ids = sample_embedding_resolver.get_hash_by_collection_id(
        session=db_session,
        collection_id=annotation_collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )
    coordinates_by_sample = {
        inside_a.sample_id: (1.0, 1.0),
        inside_b.sample_id: (5.0, 5.0),
        outside.sample_id: (100.0, 100.0),
    }
    db_session.add(
        TwoDimEmbeddingTable(
            hash=cache_key,
            x=[coordinates_by_sample[sid][0] for sid in cached_sample_ids],
            y=[coordinates_by_sample[sid][1] for sid in cached_sample_ids],
        )
    )
    db_session.commit()

    response = test_client.post(
        f"/api/collections/{annotation_collection_id}/tags/{tag.tag_id}/add/samples_by_filter",
        json={
            "filter": {
                "filter_type": "annotations",
                "embedding_region": {
                    "polygon": [
                        {"x": 0.0, "y": 0.0},
                        {"x": 10.0, "y": 0.0},
                        {"x": 10.0, "y": 10.0},
                        {"x": 0.0, "y": 10.0},
                    ]
                },
            }
        },
    )

    assert response.status_code == HTTP_STATUS_CREATED
    assert _tagged_sample_ids(session=db_session, tag_id=tag.tag_id) == {
        inside_a.sample_id,
        inside_b.sample_id,
    }


def _tagged_sample_ids(session: Session, tag_id: UUID) -> set[UUID]:
    """Read the sample ids currently linked to ``tag_id`` straight from the link table."""
    linked = session.exec(
        select(SampleTagLinkTable.sample_id).where(col(SampleTagLinkTable.tag_id) == tag_id)
    ).all()
    return {sample_id for sample_id in linked if sample_id is not None}


# `None` exercises the whole-collection scope, the image filter the grid-filter query. Both
# select all 10 samples, so the expected partition is identical.
@pytest.mark.parametrize("grid_filter", [None, {"filter_type": "image"}])
def test_split_dataset__creates_complete_tag_partition(
    db_session: Session, test_client: TestClient, grid_filter: dict[str, str] | None
) -> None:
    collection_id = create_collection(session=db_session).collection_id
    images = create_images(
        db_session=db_session,
        collection_id=collection_id,
        images=[ImageStub(path=f"s{index}.png") for index in range(10)],
    )

    response = _post_split(
        test_client,
        collection_id,
        splits=(("train", 7), ("val", 2), ("test", 1)),
        grid_filter=grid_filter,
    )

    assert response.status_code == HTTP_STATUS_CREATED
    assert response.json() == [
        {"tag_name": "train", "sample_count": 7},
        {"tag_name": "val", "sample_count": 2},
        {"tag_name": "test", "sample_count": 1},
    ]
    tagged_sample_ids = [
        _tagged_sample_ids(session=db_session, tag_id=tag.tag_id)
        for tag in tag_resolver.get_all_by_collection_id(
            session=db_session, collection_id=collection_id
        )
    ]
    # A union covering every sample plus sizes summing to the total proves the tags
    # partition the collection without overlapping.
    assert set().union(*tagged_sample_ids) == {image.sample_id for image in images}
    assert sum(len(sample_ids) for sample_ids in tagged_sample_ids) == len(images)


@pytest.mark.parametrize(
    ("sample_type", "grid_filter"),
    [
        # Video frames cannot be split, and a video filter does not apply to an image
        # collection; both must be rejected instead of silently matching nothing.
        (SampleType.VIDEO_FRAME, None),
        (SampleType.IMAGE, {"filter_type": "video"}),
    ],
)
def test_split_dataset__rejects_unsupported_collection_or_filter(
    db_session: Session,
    test_client: TestClient,
    sample_type: SampleType,
    grid_filter: dict[str, str] | None,
) -> None:
    collection_id = create_collection(session=db_session, sample_type=sample_type).collection_id

    response = _post_split(test_client, collection_id, grid_filter=grid_filter)

    assert response.status_code == HTTP_STATUS_UNPROCESSABLE_ENTITY
    assert not tag_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection_id
    )


def _post_split(
    test_client: TestClient,
    collection_id: UUID,
    *,
    splits: tuple[tuple[str, int], ...] = (("train", 1), ("test", 1)),
    grid_filter: dict[str, str] | None = None,
) -> Response:
    body: dict[str, object] = {
        "splits": [{"tag_name": name, "relative_size": size} for name, size in splits],
        "seed": 4,
    }
    if grid_filter is not None:
        body["filter"] = grid_filter
    return test_client.post(f"/api/collections/{collection_id}/tags/split", json=body)
