from sqlmodel import Session

from lightly_studio.resolvers import (
    image_resolver,
)
from tests.helpers_resolvers import (
    create_collection,
    create_image,
)


def test_get_sample_ids_by_paths__empty_input(db_session: Session) -> None:
    """Early return: empty input yields empty output."""
    collection = create_collection(session=db_session)

    result = image_resolver.get_sample_ids_by_paths(
        session=db_session,
        collection_id=collection.collection_id,
        file_paths_abs=[],
    )

    assert result == {}


def test_get_sample_ids_by_paths__returns_matching_paths(db_session: Session) -> None:
    """Returns mapping for existing paths; omits missing ones."""
    collection = create_collection(session=db_session)
    image1 = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/sample1.png",
    )
    create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/sample2.png",
    )

    result = image_resolver.get_sample_ids_by_paths(
        session=db_session,
        collection_id=collection.collection_id,
        file_paths_abs=["/path/to/sample1.png", "/path/to/missing.png"],
    )

    assert result == {"/path/to/sample1.png": image1.sample_id}


def test_get_sample_ids_by_paths__collection_isolation(db_session: Session) -> None:
    """Respects collection_id boundary; same path in different collections yields different IDs."""
    collection_a = create_collection(collection_name="collection_a", session=db_session)
    collection_b = create_collection(collection_name="collection_b", session=db_session)

    image_a = create_image(
        session=db_session,
        collection_id=collection_a.collection_id,
        file_path_abs="/path/to/sample.png",
    )
    image_b = create_image(
        session=db_session,
        collection_id=collection_b.collection_id,
        file_path_abs="/path/to/sample.png",
    )

    result_a = image_resolver.get_sample_ids_by_paths(
        session=db_session,
        collection_id=collection_a.collection_id,
        file_paths_abs=["/path/to/sample.png"],
    )
    result_b = image_resolver.get_sample_ids_by_paths(
        session=db_session,
        collection_id=collection_b.collection_id,
        file_paths_abs=["/path/to/sample.png"],
    )

    assert result_a == {"/path/to/sample.png": image_a.sample_id}
    assert result_b == {"/path/to/sample.png": image_b.sample_id}
    assert image_a.sample_id != image_b.sample_id
