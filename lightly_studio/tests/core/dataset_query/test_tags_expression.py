from __future__ import annotations

from sqlmodel import Session, select

from lightly_studio.core.dataset_query.sample_field import SampleField
from lightly_studio.models.image import ImageTable
from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import create_collection, create_image, create_tag


class TestTagsContainsExpression:
    def test_apply(self) -> None:
        expr = SampleField.tags.contains("car")
        assert expr.tag_name == "car"

    def test_apply__sql(self) -> None:
        """Test that TagsContainsExpression correctly modifies the SQL query."""
        query = select(ImageTable)
        query = query.where(SampleField.tags.contains("car").get())
        sql = str(query.compile(compile_kwargs={"literal_binds": True}))

        # The current approach makes a subquery for the tags relationship.
        assert "EXISTS (SELECT 1" in sql
        assert "FROM tag, sampletaglinktable" in sql
        assert "tag.name = 'car'" in sql

    def test_apply__can_be_chained(self, test_db: Session) -> None:
        """Test that multiple TagsContainsExpression can be applied to a query."""
        dataset = create_collection(session=test_db)
        image = create_image(session=test_db, collection_id=dataset.collection_id)
        tag = create_tag(session=test_db, collection_id=dataset.collection_id, tag_name="car")
        tag_resolver.add_tag_to_sample(session=test_db, tag_id=tag.tag_id, sample=image.sample)

        query = select(ImageTable)
        query = query.where(SampleField.tags.contains("vehicle").get())
        query = query.where(SampleField.tags.contains("car").get())

        # The sample has only one out of the two tags, no results are expected
        results = test_db.exec(query).all()
        assert len(results) == 0
