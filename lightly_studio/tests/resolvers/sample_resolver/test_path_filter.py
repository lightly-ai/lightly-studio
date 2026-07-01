from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import sample_resolver
from lightly_studio.resolvers.sample_resolver import path_filter
from tests.helpers_resolvers import create_collection, create_image
from tests.resolvers.video.helpers import VideoStub, create_videos


def test_filter_new_paths__images(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.IMAGE)
    create_image(
        session=db_session, collection_id=collection.collection_id, file_path_abs="/existing"
    )

    file_paths_new, file_paths_old = sample_resolver.filter_new_paths(
        session=db_session,
        collection_id=collection.collection_id,
        file_paths_abs=["/existing", "/new"],
    )

    assert file_paths_new == ["/new"]
    assert file_paths_old == ["/existing"]


def test_filter_new_paths__videos(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    create_videos(
        session=db_session,
        collection_id=collection.collection_id,
        videos=[VideoStub(path="/existing")],
    )

    file_paths_new, file_paths_old = sample_resolver.filter_new_paths(
        session=db_session,
        collection_id=collection.collection_id,
        file_paths_abs=["/existing", "/new"],
    )

    assert file_paths_new == ["/new"]
    assert file_paths_old == ["/existing"]


def test_filter_new_paths__scopes_to_collection(db_session: Session) -> None:
    """The same path is 'old' in the collection that has it and 'new' in another."""
    collection_a = create_collection(session=db_session, collection_name="a")
    collection_b = create_collection(session=db_session, collection_name="b")
    create_image(
        session=db_session, collection_id=collection_a.collection_id, file_path_abs="/sample.png"
    )

    new_in_a, old_in_a = sample_resolver.filter_new_paths(
        session=db_session,
        collection_id=collection_a.collection_id,
        file_paths_abs=["/sample.png"],
    )
    new_in_b, old_in_b = sample_resolver.filter_new_paths(
        session=db_session,
        collection_id=collection_b.collection_id,
        file_paths_abs=["/sample.png"],
    )

    assert (new_in_a, old_in_a) == ([], ["/sample.png"])
    assert (new_in_b, old_in_b) == (["/sample.png"], [])


def test_filter_new_paths__batches_over_postgres_param_limit(db_session: Session) -> None:
    """More paths than PostgreSQL's 65,535-parameter cap are handled by internal batching."""
    collection = create_collection(session=db_session)
    file_paths_abs = [f"/p/{i}.png" for i in range(70_000)]

    file_paths_new, file_paths_old = sample_resolver.filter_new_paths(
        session=db_session,
        collection_id=collection.collection_id,
        file_paths_abs=file_paths_abs,
    )

    assert len(file_paths_new) == 70_000
    assert file_paths_old == []


def test_get_existing_paths__empty_collection(db_session: Session) -> None:
    collection = create_collection(session=db_session)

    existing_paths = sample_resolver.get_existing_paths(
        session=db_session, collection_id=collection.collection_id
    )

    assert existing_paths == set()


def test_get_existing_paths__images(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.IMAGE)
    create_image(session=db_session, collection_id=collection.collection_id, file_path_abs="/a.png")
    create_image(session=db_session, collection_id=collection.collection_id, file_path_abs="/b.png")

    existing_paths = sample_resolver.get_existing_paths(
        session=db_session, collection_id=collection.collection_id
    )

    assert existing_paths == {"/a.png", "/b.png"}


def test_get_existing_paths__videos(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    create_videos(
        session=db_session,
        collection_id=collection.collection_id,
        videos=[VideoStub(path="/a.mp4"), VideoStub(path="/b.mp4")],
    )

    existing_paths = sample_resolver.get_existing_paths(
        session=db_session, collection_id=collection.collection_id
    )

    assert existing_paths == {"/a.mp4", "/b.mp4"}


def test_get_existing_paths__scopes_to_collection(db_session: Session) -> None:
    """A path in one collection does not show up as existing in another."""
    collection_a = create_collection(session=db_session, collection_name="a")
    collection_b = create_collection(session=db_session, collection_name="b")
    create_image(
        session=db_session, collection_id=collection_a.collection_id, file_path_abs="/sample.png"
    )

    existing_in_a = sample_resolver.get_existing_paths(
        session=db_session, collection_id=collection_a.collection_id
    )
    existing_in_b = sample_resolver.get_existing_paths(
        session=db_session, collection_id=collection_b.collection_id
    )

    assert existing_in_a == {"/sample.png"}
    assert existing_in_b == set()


def test__resolve_path_column__rejects_unsupported_sample_type(db_session: Session) -> None:
    """An unsupported sample type fails with a clear error listing types by value."""
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO_FRAME)

    with pytest.raises(ValueError, match="does not support sample type") as exc_info:
        path_filter._resolve_path_column(session=db_session, collection_id=collection.collection_id)

    assert "supported types are ['image', 'video']" in str(exc_info.value)
