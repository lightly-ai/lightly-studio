from __future__ import annotations

from duckdb_engine import Dialect as DuckDBDialect
from sqlmodel import select

from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.order_by import OrderByField, OrderByMetadataField
from lightly_studio.models.image import ImageTable


class TestOrderByField:
    def test_apply__default_ascending(self) -> None:
        """Test that default ordering is ascending."""
        query = select(ImageTable)
        order_by = OrderByField(ImageSampleField.file_name)

        returned_query = order_by.apply(query)

        sql = str(returned_query.compile(compile_kwargs={"literal_binds": True})).lower()
        assert "order by image.file_name asc" in sql

    def test_apply__descending(self) -> None:
        """Test descending ordering via desc() method."""
        query = select(ImageTable)
        order_by = OrderByField(ImageSampleField.file_name).desc()

        returned_query = order_by.apply(query)

        sql = str(returned_query.compile(compile_kwargs={"literal_binds": True})).lower()
        assert "order by image.file_name desc" in sql

    def test_apply__desc_then_asc(self) -> None:
        """Test that desc().asc() returns to ascending order."""
        query = select(ImageTable)
        order_by = OrderByField(ImageSampleField.file_name).desc().asc()

        returned_query = order_by.apply(query)

        sql = str(returned_query.compile(compile_kwargs={"literal_binds": True})).lower()
        assert "order by image.file_name asc" in sql


class TestOrderByMetadataField:
    dialect = DuckDBDialect()

    def test_apply__default_ascending(self) -> None:
        """Test that default ordering is ascending."""
        query = select(ImageTable)
        order_by = OrderByMetadataField("brightness")

        returned_query = order_by.apply(query)

        sql = str(
            returned_query.compile(dialect=self.dialect, compile_kwargs={"literal_binds": True})
        ).lower()
        assert "order by json_extract(metadata.data, '$.brightness') asc" in sql

    def test_apply__descending(self) -> None:
        """Test descending ordering via desc() method."""
        query = select(ImageTable)
        order_by = OrderByMetadataField("brightness").desc()

        returned_query = order_by.apply(query)

        sql = str(
            returned_query.compile(dialect=self.dialect, compile_kwargs={"literal_binds": True})
        ).lower()
        assert "order by json_extract(metadata.data, '$.brightness') desc" in sql

    def test_apply__desc_then_asc(self) -> None:
        """Test that desc().asc() returns to ascending order."""
        query = select(ImageTable)
        order_by = OrderByMetadataField("brightness").desc().asc()

        returned_query = order_by.apply(query)

        sql = str(
            returned_query.compile(dialect=self.dialect, compile_kwargs={"literal_binds": True})
        ).lower()
        assert "order by json_extract(metadata.data, '$.brightness') asc" in sql

    def test_apply__cast_to_float(self) -> None:
        """Test that cast_to_float produces a CAST expression in the ORDER BY clause."""
        query = select(ImageTable)
        order_by = OrderByMetadataField("score", cast_to_float=True)

        returned_query = order_by.apply(query)

        sql = str(
            returned_query.compile(dialect=self.dialect, compile_kwargs={"literal_binds": True})
        ).lower()
        assert "order by cast(json_extract(metadata.data, '$.score') as float) asc" in sql
