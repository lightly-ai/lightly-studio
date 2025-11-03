from sqlmodel import Session

from lightly_studio.resolvers import (
    image_resolver,
)
from tests.helpers_resolvers import (
    create_dataset,
    create_image,
)


def test_count_by_dataset_id(test_db: Session) -> None:
    """Test counting samples by dataset ID."""
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    # Initially should be 0
    assert image_resolver.count_by_dataset_id(session=test_db, dataset_id=dataset_id) == 0

    # Create some samples
    for i in range(3):
        create_image(
            session=test_db,
            dataset_id=dataset_id,
            file_path_abs=f"/path/to/sample{i}.png",
        )

    # Should now count 3 samples
    assert image_resolver.count_by_dataset_id(session=test_db, dataset_id=dataset_id) == 3

    # Create another dataset to ensure count is dataset-specific
    dataset2 = create_dataset(session=test_db, dataset_name="dataset2")
    dataset2_id = dataset2.dataset_id

    create_image(
        session=test_db,
        dataset_id=dataset2_id,
        file_path_abs="/path/to/other_sample.png",
    )

    # Counts should be independent
    assert image_resolver.count_by_dataset_id(session=test_db, dataset_id=dataset_id) == 3
    assert image_resolver.count_by_dataset_id(session=test_db, dataset_id=dataset2_id) == 1
