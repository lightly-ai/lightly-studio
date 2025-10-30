from sqlmodel import Session

from lightly_studio.models.image import ImageCreate
from lightly_studio.resolvers import image_resolver_legacy, tag_resolver
from lightly_studio.resolvers.samples_filter import SampleFilter
from tests.helpers_resolvers import (
    create_dataset,
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
        sample1 = image_resolver_legacy.create(
            session=test_db,
            sample=ImageCreate(
                dataset_id=dataset_id,
                file_path_abs="/path/to/sample1.png",
                file_name="sample1.png",
                width=100,
                height=100,
            ),
        )
        _sample2 = image_resolver_legacy.create(
            session=test_db,
            sample=ImageCreate(
                dataset_id=dataset_id,
                file_path_abs="/path/to/sample2.png",
                file_name="sample2.png",
                width=200,
                height=200,
            ),
        )

        # Create a tag for sample1.
        dog_tag = create_tag(
            session=test_db,
            dataset_id=dataset_id,
            tag_name="dog",
            kind="sample",
        )
        tag_resolver.add_sample_ids_to_tag_id(
            session=test_db,
            tag_id=dog_tag.tag_id,
            sample_ids=[sample1.sample_id],
        )

        # Test get_samples.
        # All.
        samples = dataset.get_samples()
        assert len(samples) == 2

        # By tag.
        samples = dataset.get_samples(filters=SampleFilter(tag_ids=[dog_tag.tag_id]))
        assert len(samples) == 1
        assert samples[0].sample_id == sample1.sample_id

        # With a limit. Default ordering is by created_at, so sample1 comes first.
        samples = dataset.get_samples(limit=1)
        assert len(samples) == 1
        assert samples[0].sample_id == sample1.sample_id
