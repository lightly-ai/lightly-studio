from sqlmodel import Session

from lightly_studio.resolvers import (
    image_resolver,
)
from tests.helpers_resolvers import (
    create_dataset,
    create_image,
)


def test_filter_new_paths(test_db: Session) -> None:
    # 1. Case: empty DB, all paths are new
    dataset = create_dataset(session=test_db)

    file_paths_new, file_paths_old = image_resolver.filter_new_paths(
        session=test_db, file_paths_abs=["/path/to/sample.png"]
    )

    assert file_paths_new == ["/path/to/sample.png"]
    assert file_paths_old == []

    # Case 2: db non empty, same paths are new same are old
    create_image(
        session=test_db,
        dataset_id=dataset.dataset_id,
        file_path_abs="/path/to/sample.png",
    )

    file_paths_new, file_paths_old = image_resolver.filter_new_paths(
        session=test_db, file_paths_abs=["/path/to/sample.png", "/path/to/sample_new.png"]
    )

    assert file_paths_new == ["/path/to/sample_new.png"]
    assert file_paths_old == ["/path/to/sample.png"]

    # Case 2: db non empty, only old
    file_paths_new, file_paths_old = image_resolver.filter_new_paths(
        session=test_db, file_paths_abs=["/path/to/sample.png"]
    )

    assert file_paths_new == []
    assert file_paths_old == ["/path/to/sample.png"]

    # Case 3: db non empty, empty request
    file_paths_new, file_paths_old = image_resolver.filter_new_paths(
        session=test_db, file_paths_abs=[]
    )

    assert file_paths_new == []
    assert file_paths_old == []
