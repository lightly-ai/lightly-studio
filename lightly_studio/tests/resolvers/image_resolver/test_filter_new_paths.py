from sqlmodel import Session

from lightly_studio.resolvers import (
    image_resolver,
)
from tests.helpers_resolvers import (
    create_collection,
    create_image,
)


def test_filter_new_paths(test_db: Session) -> None:
    # 1. Case: empty DB, all paths are new
    collection = create_collection(session=test_db)

    file_paths_new, file_paths_old = image_resolver.filter_new_paths(
        session=test_db,
        collection_id=collection.collection_id,
        file_paths_abs=["/path/to/sample.png"],
    )

    assert file_paths_new == ["/path/to/sample.png"]
    assert file_paths_old == []

    # Case 2: db non empty, same paths are new same are old
    create_image(
        session=test_db,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/sample.png",
    )

    file_paths_new, file_paths_old = image_resolver.filter_new_paths(
        session=test_db,
        collection_id=collection.collection_id,
        file_paths_abs=["/path/to/sample.png", "/path/to/sample_new.png"],
    )

    assert file_paths_new == ["/path/to/sample_new.png"]
    assert file_paths_old == ["/path/to/sample.png"]

    # Case 3: db non empty, only old
    file_paths_new, file_paths_old = image_resolver.filter_new_paths(
        session=test_db,
        collection_id=collection.collection_id,
        file_paths_abs=["/path/to/sample.png"],
    )

    assert file_paths_new == []
    assert file_paths_old == ["/path/to/sample.png"]

    # Case 4: db non empty, empty request
    file_paths_new, file_paths_old = image_resolver.filter_new_paths(
        session=test_db,
        collection_id=collection.collection_id,
        file_paths_abs=[],
    )

    assert file_paths_new == []
    assert file_paths_old == []


def test_filter_new_paths_same_path_different_collections(test_db: Session) -> None:
    """The same file_path_abs can be added to different collections independently."""
    collection_a = create_collection(collection_name="collection_a", session=test_db)
    collection_b = create_collection(collection_name="collection_b", session=test_db)

    # Add sample to collection A
    create_image(
        session=test_db,
        collection_id=collection_a.collection_id,
        file_path_abs="/path/to/sample.png",
    )

    # The path should be "old" in collection A
    file_paths_new, file_paths_old = image_resolver.filter_new_paths(
        session=test_db,
        collection_id=collection_a.collection_id,
        file_paths_abs=["/path/to/sample.png"],
    )
    assert file_paths_new == []
    assert file_paths_old == ["/path/to/sample.png"]

    # The same path should be "new" in collection B
    file_paths_new, file_paths_old = image_resolver.filter_new_paths(
        session=test_db,
        collection_id=collection_b.collection_id,
        file_paths_abs=["/path/to/sample.png"],
    )
    assert file_paths_new == ["/path/to/sample.png"]
    assert file_paths_old == []
