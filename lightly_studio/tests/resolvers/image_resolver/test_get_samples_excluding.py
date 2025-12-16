from sqlmodel import Session

from lightly_studio.resolvers import (
    image_resolver,
)
from tests.helpers_resolvers import (
    create_dataset,
    create_image,
)


def test_get_samples_excluding(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id

    # create samples
    image1 = create_image(
        session=test_db,
        dataset_id=dataset_id,
        file_path_abs="/path/to/sample1.png",
    )
    image2 = create_image(
        session=test_db,
        dataset_id=dataset_id,
        file_path_abs="/path/to/sample2.png",
    )
    image3 = create_image(
        session=test_db,
        dataset_id=dataset_id,
        file_path_abs="/path/to/sample3.png",
    )
    image4 = create_image(
        session=test_db,
        dataset_id=dataset_id,
        file_path_abs="/path/to/sample4.png",
    )

    # Retrieve Samples
    images = image_resolver.get_samples_excluding(
        session=test_db,
        dataset_id=dataset_id,
        excluded_sample_ids=[image1.sample_id],
    )

    # Assert
    assert len(images) == 3
    returned_sample_ids = [sample.sample_id for sample in images]
    assert image1.sample_id not in returned_sample_ids
    assert sorted(returned_sample_ids) == sorted(
        [
            image2.sample_id,
            image3.sample_id,
            image4.sample_id,
        ]
    )
    # Retrieve Samples
    images = image_resolver.get_samples_excluding(
        session=test_db,
        dataset_id=dataset_id,
        excluded_sample_ids=[image1.sample_id],
        limit=2,
    )

    # Assert
    assert len(images) == 2
