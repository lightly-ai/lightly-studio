from __future__ import annotations

from duckdb_engine import Dialect as DuckDBDialect
from sqlmodel import select

from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.order_by import (
    OrderByEvaluationMetricField,
    OrderByField,
    OrderByMetadataField,
)
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
        order_by = OrderByMetadataField("brightness", cast_to_float=False)

        returned_query = order_by.apply(query)

        sql = str(
            returned_query.compile(dialect=self.dialect, compile_kwargs={"literal_binds": True})
        ).lower()
        assert "order by json_extract(metadata.data, '$.brightness') asc" in sql

    def test_apply__descending(self) -> None:
        """Test descending ordering via desc() method."""
        query = select(ImageTable)
        order_by = OrderByMetadataField("brightness", cast_to_float=False).desc()

        returned_query = order_by.apply(query)

        sql = str(
            returned_query.compile(dialect=self.dialect, compile_kwargs={"literal_binds": True})
        ).lower()
        assert "order by json_extract(metadata.data, '$.brightness') desc" in sql

    def test_apply__desc_then_asc(self) -> None:
        """Test that desc().asc() returns to ascending order."""
        query = select(ImageTable)
        order_by = OrderByMetadataField("brightness", cast_to_float=False).desc().asc()

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


class TestOrderByEvaluationMetricField:
    dialect = DuckDBDialect()

    def test_apply__default_ascending(self) -> None:
        """Test that default ordering is ascending with the expected JOINs."""
        query = select(ImageTable)
        order_by = OrderByEvaluationMetricField("run1", "score")

        returned_query = order_by.apply(query)

        sql = str(
            returned_query.compile(dialect=self.dialect, compile_kwargs={"literal_binds": True})
        ).lower()
        assert "left outer join evaluation_run" in sql
        assert "left outer join evaluation_sample_metric" in sql
        assert "evaluation_sample_metric.metric_name = 'score'" in sql
        assert "order by evaluation_sample_metric.value asc" in sql

    def test_apply__descending(self) -> None:
        """Test descending ordering via desc() method."""
        query = select(ImageTable)
        order_by = OrderByEvaluationMetricField("run1", "score").desc()

        returned_query = order_by.apply(query)

        sql = str(
            returned_query.compile(dialect=self.dialect, compile_kwargs={"literal_binds": True})
        ).lower()
        assert "order by evaluation_sample_metric.value desc" in sql

    def test_apply__desc_then_asc(self) -> None:
        """Test that desc().asc() returns to ascending order."""
        query = select(ImageTable)
        order_by = OrderByEvaluationMetricField("run1", "score").desc().asc()

        returned_query = order_by.apply(query)

        sql = str(
            returned_query.compile(dialect=self.dialect, compile_kwargs={"literal_binds": True})
        ).lower()
        assert "order by evaluation_sample_metric.value asc" in sql

    def test_to_column_element__ascending(self) -> None:
        """Test that to_column_element returns only the column element without any JOIN."""
        order_by = OrderByEvaluationMetricField("run1", "score")

        col_element = order_by.to_column_element()

        sql = str(col_element.compile(compile_kwargs={"literal_binds": True})).lower()
        assert "evaluation_sample_metric.value asc" in sql
        assert "join" not in sql
