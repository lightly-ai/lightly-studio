from __future__ import annotations

from sqlmodel import Session, select

from lightly_studio.core.dataset_query.sample_field import SampleField
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import create_dataset, create_sample, create_tag


class TestTagsContainsExpression:
    def test_apply(self) -> None:
        expr = SampleField.tags.contains("car")
        assert expr.tag_name == "car"

    def test_apply__sql(self) -> None:
        """Test that TagsContainsExpression correctly modifies the SQL query."""
        query = select(SampleTable)
        query = query.where(SampleField.tags.contains("car").get())
        sql = str(query.compile(compile_kwargs={"literal_binds": True}))

        # The current approach makes a subquery for the tags relationship.
        assert "EXISTS (SELECT 1" in sql
        assert "FROM tags, sampletaglinktable" in sql
        assert "tags.name = 'car'" in sql

    def test_apply__can_be_chained(self, test_db: Session) -> None:
        """Test that multiple TagsContainsExpression can be applied to a query."""
        dataset = create_dataset(session=test_db)
        sample = create_sample(session=test_db, dataset_id=dataset.dataset_id)
        tag = create_tag(session=test_db, dataset_id=dataset.dataset_id, tag_name="car")
        tag_resolver.add_tag_to_sample(session=test_db, tag_id=tag.tag_id, sample=sample)

        query = select(SampleTable)
        query = query.where(SampleField.tags.contains("vehicle").get())
        query = query.where(SampleField.tags.contains("car").get())

        # The sample has only one out of the two tags, no results are expected
        results = test_db.exec(query).all()
        assert len(results) == 0
