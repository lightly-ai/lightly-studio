from sqlmodel import Session

from lightly_studio.resolvers import tag_resolver
from lightly_studio.resolvers.samples_filter import SampleFilter
from tests.helpers_resolvers import (
    SampleImage,
    create_dataset,
    create_images,
    create_tag,
)


class TestDatasetTable:
    def test_get_samples(
        self,
        test_db: Session,
    ) -> None:
        """Test retrieving samples from a dataset with various filters.

        Probe test, does not test all possible filters.
        """
        dataset = create_dataset(session=test_db)
        dataset_id = dataset.dataset_id

        # Create samples.
        images = create_images(
            db_session=test_db,
            dataset_id=dataset_id,
            images=[
                SampleImage(path="sample1.png", width=100, height=100),
                SampleImage(path="sample2.png", width=200, height=200),
            ],
        )
        image_0_id = images[0].sample_id

        # Create a tag for image 0.
        dog_tag = create_tag(
            session=test_db,
            dataset_id=dataset_id,
            tag_name="dog",
            kind="sample",
        )
        tag_resolver.add_sample_ids_to_tag_id(
            session=test_db,
            tag_id=dog_tag.tag_id,
            sample_ids=[image_0_id],
        )

        # Test get_samples.
        # All.
        samples = dataset.get_samples()
        assert len(samples) == 2

        # By tag.
        samples = dataset.get_samples(filters=SampleFilter(tag_ids=[dog_tag.tag_id]))
        assert len(samples) == 1
        assert samples[0].sample_id == image_0_id

        # With a limit. Default ordering is by created_at, so image 0 comes first.
        samples = dataset.get_samples(limit=1)
        assert len(samples) == 1
        assert samples[0].sample_id == image_0_id
