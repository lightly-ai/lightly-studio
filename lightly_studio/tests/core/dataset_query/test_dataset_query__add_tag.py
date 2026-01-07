from __future__ import annotations

from sqlmodel import Session

from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.order_by import OrderByField
from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import create_collection, create_image, create_tag


class TestDatasetQueryAddTag:
    def test_add_tag__with_expressions(self, test_db: Session) -> None:
        """Test add_tag with a filter only tags matching samples."""
        # Arrange
        dataset = create_collection(session=test_db)

        # Create samples with different widths in non-increasing order
        image40 = create_image(
            session=test_db,
            collection_id=dataset.collection_id,
            file_path_abs="/path/to/sample40.png",
            width=40,
        )
        image10 = create_image(
            session=test_db,
            collection_id=dataset.collection_id,
            file_path_abs="/path/to/sample10.png",
            width=10,
        )
        image30 = create_image(
            session=test_db,
            collection_id=dataset.collection_id,
            file_path_abs="/path/to/sample30.png",
            width=30,
        )
        image20 = create_image(
            session=test_db,
            collection_id=dataset.collection_id,
            file_path_abs="/path/to/sample20.png",
            width=20,
        )

        # Add a tag to the smallest 2 samples with width > 15: sample20 and sample30
        query = DatasetQuery(dataset=dataset, session=test_db)
        query.match(ImageSampleField.width > 15).order_by(
            OrderByField(ImageSampleField.width)
        ).slice(limit=2)
        query.add_tag(tag_name="my_tag")

        # Verify tag was created
        tag = tag_resolver.get_by_name(
            session=test_db, tag_name="my_tag", collection_id=dataset.collection_id
        )
        assert tag is not None
        assert tag.name == "my_tag"
        assert tag.kind == "sample"

        # Refresh samples to get updated tags
        test_db.refresh(image10)
        test_db.refresh(image20)
        test_db.refresh(image30)
        test_db.refresh(image40)

        # Assert - only sample20 and sample30 should have the tag
        assert tag not in image10.sample.tags
        assert tag in image20.sample.tags
        assert tag in image30.sample.tags
        assert tag not in image40.sample.tags

    def test_add_tag__no_expressions(self, test_db: Session) -> None:
        """Test add_tag without any filter tags all samples."""
        # Arrange
        dataset = create_collection(session=test_db)
        image1 = create_image(
            session=test_db,
            collection_id=dataset.collection_id,
            file_path_abs="/path/to/sample1.png",
        )
        image2 = create_image(
            session=test_db,
            collection_id=dataset.collection_id,
            file_path_abs="/path/to/sample2.png",
        )

        # Add a tag to all samples
        query = DatasetQuery(dataset=dataset, session=test_db)
        query.add_tag(tag_name="my_tag")

        # Assert - verify tag was created
        tag = tag_resolver.get_by_name(
            session=test_db, tag_name="my_tag", collection_id=dataset.collection_id
        )
        assert tag is not None

        # Assert - both samples should have the tag
        test_db.refresh(image1)
        test_db.refresh(image2)
        assert tag in image1.sample.tags
        assert tag in image2.sample.tags

    def test_add_tag__double_tag(self, test_db: Session) -> None:
        """Test add_tag does not double-tag samples."""
        # Arrange
        dataset = create_collection(session=test_db)
        image = create_image(
            session=test_db,
            collection_id=dataset.collection_id,
        )

        # Add a tag
        query = DatasetQuery(dataset=dataset, session=test_db)
        query.add_tag(tag_name="my_tag")

        # Add the same tag again
        query = DatasetQuery(dataset=dataset, session=test_db)
        query.add_tag(tag_name="my_tag")

        # Assert - the sample should have the tag only once
        test_db.refresh(image)
        assert len(image.sample.tags) == 1

    def test_add_tag__empty_query(self, test_db: Session) -> None:
        """Test add_tag on an empty query does not create a tag."""
        # Arrange
        dataset = create_collection(session=test_db)
        image = create_image(
            session=test_db,
            collection_id=dataset.collection_id,
            width=10,
        )

        # Add a tag with a query that matches no samples
        query = DatasetQuery(dataset=dataset, session=test_db)
        query.match(ImageSampleField.width > 999)
        query.add_tag(tag_name="example_tag")

        # The tag should have been created
        tag = tag_resolver.get_by_name(
            session=test_db, tag_name="example_tag", collection_id=dataset.collection_id
        )
        assert tag is not None

        # The sample should not have the tag
        test_db.refresh(image)
        assert image.sample.tags == []

    def test_add_tag__some_already_tagged(self, test_db: Session) -> None:
        """Test add_tag on a query where some samples are already tagged."""
        # Arrange
        dataset = create_collection(session=test_db)
        image1 = create_image(
            session=test_db,
            collection_id=dataset.collection_id,
            file_path_abs="/path/to/sample1.png",
        )
        image2 = create_image(
            session=test_db,
            collection_id=dataset.collection_id,
            file_path_abs="/path/to/sample2.png",
        )

        # Pre-tag sample2 with "example_tag"
        tag = create_tag(
            session=test_db,
            collection_id=dataset.collection_id,
            tag_name="my_tag",
        )
        tag_resolver.add_tag_to_sample(session=test_db, tag_id=tag.tag_id, sample=image2.sample)

        # Add the tag to all samples
        query = DatasetQuery(dataset=dataset, session=test_db)
        query.add_tag(tag_name="my_tag")

        # Assert - all samples should have the tag, but it should not be duplicated for sample2
        test_db.refresh(image1)
        test_db.refresh(image2)
        assert image1.sample.tags == [tag]
        assert image2.sample.tags == [tag]
