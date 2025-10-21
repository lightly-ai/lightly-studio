from __future__ import annotations

from sqlmodel import select

from lightly_studio.core.dataset_query.order_by import OrderByField
from lightly_studio.core.dataset_query.sample_field import SampleField
from lightly_studio.models.sample import ImageTable


class TestOrderByField:
    def test_apply__default_ascending(self) -> None:
        """Test that default ordering is ascending."""
        query = select(ImageTable)
        order_by = OrderByField(SampleField.file_name)

        returned_query = order_by.apply(query)

        sql = str(returned_query.compile(compile_kwargs={"literal_binds": True})).lower()
        assert "order by sample.file_name asc" in sql

    def test_apply__descending(self) -> None:
        """Test descending ordering via desc() method."""
        query = select(ImageTable)
        order_by = OrderByField(SampleField.file_name).desc()

        returned_query = order_by.apply(query)

        sql = str(returned_query.compile(compile_kwargs={"literal_binds": True})).lower()
        assert "order by sample.file_name desc" in sql

    def test_apply__desc_then_asc(self) -> None:
        """Test that desc().asc() returns to ascending order."""
        query = select(ImageTable)
        order_by = OrderByField(SampleField.file_name).desc().asc()

        returned_query = order_by.apply(query)

        sql = str(returned_query.compile(compile_kwargs={"literal_binds": True})).lower()
        assert "order by sample.file_name asc" in sql
