from __future__ import annotations

import pytest
from sqlmodel import Session, select

from lightly_studio.core.dataset_query.tags_expression import TagsAccessor
from lightly_studio.models.image import ImageTable
from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import create_collection, create_image, create_tag


class TestTagsContainsExpression:
    def test_apply(self) -> None:
        expr = TagsAccessor().contains("car")
        assert expr.tag_names == ("car",)

    def test_apply__multiple_tags(self) -> None:
        expr = TagsAccessor().contains(["car", "vehicle"])
        assert expr.tag_names == ("car", "vehicle")

    def test_apply__tag_name_set(self) -> None:
        expr = TagsAccessor().contains({"car", "vehicle"})
        assert set(expr.tag_names) == {"car", "vehicle"}

    def test_apply__no_tags(self) -> None:
        with pytest.raises(ValueError, match="At least one tag name must be passed"):
            TagsAccessor().contains([])

    def test_apply__sql(self) -> None:
        """Test that TagsContainsExpression correctly modifies the SQL query."""
        query = select(ImageTable)
        query = query.where(TagsAccessor().contains("car").get())
        sql = str(query.compile(compile_kwargs={"literal_binds": True}))

        # The current approach makes a subquery for the tags relationship.
        assert "EXISTS (SELECT 1" in sql
        assert "FROM tag, sampletaglinktable" in sql
        assert "tag.name = 'car'" in sql

    def test_apply__sql_multiple_tags(self) -> None:
        """Test that multiple tag names are combined with AND in the SQL query."""
        query = select(ImageTable)
        query = query.where(TagsAccessor().contains(["car", "vehicle"]).get())
        sql = str(query.compile(compile_kwargs={"literal_binds": True}))

        # One subquery per tag name, all of which must match.
        assert sql.count("EXISTS (SELECT 1") == 2
        assert "tag.name = 'car'" in sql
        assert "tag.name = 'vehicle'" in sql
        assert " AND " in sql

    def test_apply__multiple_tags_all_assigned(self, db_session: Session) -> None:
        """Test that a sample with all of the tags is matched."""
        dataset = create_collection(session=db_session)
        image = create_image(session=db_session, collection_id=dataset.collection_id)
        for tag_name in ("car", "vehicle"):
            tag = create_tag(
                session=db_session, collection_id=dataset.collection_id, tag_name=tag_name
            )
            tag_resolver.add_tag_to_sample(
                session=db_session, tag_id=tag.tag_id, sample=image.sample
            )

        query = select(ImageTable).where(TagsAccessor().contains(["car", "vehicle"]).get())

        results = db_session.exec(query).all()
        assert len(results) == 1

    def test_apply__multiple_tags_partially_assigned(self, db_session: Session) -> None:
        """Test that a sample with only some of the tags is not matched."""
        dataset = create_collection(session=db_session)
        image = create_image(session=db_session, collection_id=dataset.collection_id)
        tag = create_tag(session=db_session, collection_id=dataset.collection_id, tag_name="car")
        tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag.tag_id, sample=image.sample)

        query = select(ImageTable).where(TagsAccessor().contains(["car", "vehicle"]).get())

        # The sample has only one out of the two tags, no results are expected
        results = db_session.exec(query).all()
        assert len(results) == 0

    def test_apply__can_be_chained(self, db_session: Session) -> None:
        """Test that multiple TagsContainsExpression can be applied to a query."""
        dataset = create_collection(session=db_session)
        image = create_image(session=db_session, collection_id=dataset.collection_id)
        tag = create_tag(session=db_session, collection_id=dataset.collection_id, tag_name="car")
        tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag.tag_id, sample=image.sample)

        query = select(ImageTable)
        query = query.where(TagsAccessor().contains("vehicle").get())
        query = query.where(TagsAccessor().contains("car").get())

        # The sample has only one out of the two tags, no results are expected
        results = db_session.exec(query).all()
        assert len(results) == 0
