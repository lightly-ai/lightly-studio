from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.image import ImageTable
from lightly_studio.models.video import VideoTable
from lightly_studio.resolvers import sample_resolver
from tests.helpers_resolvers import create_collection, create_image
from tests.resolvers.video.helpers import VideoStub, create_videos


def _create_image(session: Session, collection_id: UUID, file_path_abs: str) -> None:
    create_image(session=session, collection_id=collection_id, file_path_abs=file_path_abs)


def _create_video(session: Session, collection_id: UUID, file_path_abs: str) -> None:
    create_videos(
        session=session, collection_id=collection_id, videos=[VideoStub(path=file_path_abs)]
    )


# (model, collection sample type, helper that inserts one sample with a given path).
_MODEL_CASES = [
    pytest.param(ImageTable, SampleType.IMAGE, _create_image, id="image"),
    pytest.param(VideoTable, SampleType.VIDEO, _create_video, id="video"),
]


@pytest.mark.parametrize(("model", "sample_type", "create_sample"), _MODEL_CASES)
def test_filter_new_paths_splits_existing_from_new(
    db_session: Session,
    model: type[ImageTable] | type[VideoTable],
    sample_type: SampleType,
    create_sample: Callable[[Session, UUID, str], None],
) -> None:
    collection = create_collection(session=db_session, sample_type=sample_type)
    create_sample(db_session, collection.collection_id, "/existing")

    file_paths_new, file_paths_old = sample_resolver.filter_new_paths(
        session=db_session,
        collection_id=collection.collection_id,
        file_paths_abs=["/existing", "/new"],
        model=model,
    )

    assert file_paths_new == ["/new"]
    assert file_paths_old == ["/existing"]


def test_filter_new_paths_scopes_to_collection(db_session: Session) -> None:
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
        model=ImageTable,
    )
    new_in_b, old_in_b = sample_resolver.filter_new_paths(
        session=db_session,
        collection_id=collection_b.collection_id,
        file_paths_abs=["/sample.png"],
        model=ImageTable,
    )

    assert (new_in_a, old_in_a) == ([], ["/sample.png"])
    assert (new_in_b, old_in_b) == (["/sample.png"], [])


def test_filter_new_paths_batches_over_postgres_param_limit(db_session: Session) -> None:
    """More paths than PostgreSQL's 65,535-parameter cap are handled by internal batching."""
    collection = create_collection(session=db_session)
    file_paths_abs = [f"/p/{i}.png" for i in range(70_000)]

    file_paths_new, file_paths_old = sample_resolver.filter_new_paths(
        session=db_session,
        collection_id=collection.collection_id,
        file_paths_abs=file_paths_abs,
        model=ImageTable,
    )

    assert len(file_paths_new) == 70_000
    assert file_paths_old == []
