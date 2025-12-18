from sqlmodel import Session

from lightly_studio.resolvers import (
    image_resolver,
)
from tests.helpers_resolvers import (
    create_collection,
    create_image,
)


def test_get_many_by_id(
    test_db: Session,
) -> None:
    dataset = create_collection(session=test_db)
    dataset_id = dataset.collection_id
    # Create samples.
    image1 = create_image(
        session=test_db,
        collection_id=dataset_id,
        file_path_abs="/path/to/sample1.png",
    )
    image2 = create_image(
        session=test_db,
        collection_id=dataset_id,
        file_path_abs="/path/to/sample2.png",
    )

    # Act.
    samples = image_resolver.get_many_by_id(
        session=test_db, sample_ids=[image1.sample_id, image2.sample_id]
    )

    # Assert.
    assert len(samples) == 2
    assert samples[0].file_name == "sample1.png"
    assert samples[1].file_name == "sample2.png"
