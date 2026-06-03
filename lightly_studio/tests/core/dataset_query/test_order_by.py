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
    def test_apply_select_join__add_order_value(self) -> None:
        """Test that add_order_value appends the sort column to the SELECT list."""
        query = select(ImageTable)
        order_by = OrderByField(ImageSampleField.file_name)

        returned_query, order_value_index = order_by.apply_select_join(
            query, add_order_value=True
        )

        sql = str(returned_query.compile(compile_kwargs={"literal_binds": True})).lower()
        assert "select image" in sql
        assert "image.file_name" in sql
        assert order_value_index == 1

    def test_apply_select_join__no_joins(self) -> None:
        """Test that apply_select_join does not add JOINs for image fields."""
        query = select(ImageTable)
        order_by = OrderByField(ImageSampleField.file_name)

        returned_query, order_value_index = order_by.apply_select_join(query)

        sql = str(returned_query.compile(compile_kwargs={"literal_binds": True})).lower()
        assert "join" not in sql
        assert order_value_index is None

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

    def test_apply_select_join__metadata_join(self) -> None:
        """Test that apply_select_join adds the metadata outer join."""
        query = select(ImageTable)
        order_by = OrderByMetadataField("brightness", cast_to_float=False)

        returned_query, order_value_index = order_by.apply_select_join(query)

        sql = str(
            returned_query.compile(dialect=self.dialect, compile_kwargs={"literal_binds": True})
        ).lower()
        assert "left outer join metadata" in sql
        assert order_value_index is None

    def test_apply_select_join__add_order_value(self) -> None:
        """Test that add_order_value selects the JSON extract expression."""
        query = select(ImageTable)
        order_by = OrderByMetadataField("score", cast_to_float=True)

        returned_query, order_value_index = order_by.apply_select_join(
            query, add_order_value=True
        )

        sql = str(
            returned_query.compile(dialect=self.dialect, compile_kwargs={"literal_binds": True})
        ).lower()
        assert "left outer join metadata" in sql
        assert "json_extract(metadata_1.data, '$.score')" in sql
        assert order_value_index == 1

    def test_apply__default_ascending(self) -> None:
        """Test that default ordering is ascending."""
        query = select(ImageTable)
        order_by = OrderByMetadataField("brightness", cast_to_float=False)

        returned_query = order_by.apply(query)

        sql = str(
            returned_query.compile(dialect=self.dialect, compile_kwargs={"literal_binds": True})
        ).lower()
        assert "order by json_extract(metadata_1.data, '$.brightness') asc" in sql

    def test_apply__descending(self) -> None:
        """Test descending ordering via desc() method."""
        query = select(ImageTable)
        order_by = OrderByMetadataField("brightness", cast_to_float=False).desc()

        returned_query = order_by.apply(query)

        sql = str(
            returned_query.compile(dialect=self.dialect, compile_kwargs={"literal_binds": True})
        ).lower()
        assert "order by json_extract(metadata_1.data, '$.brightness') desc" in sql

    def test_apply__desc_then_asc(self) -> None:
        """Test that desc().asc() returns to ascending order."""
        query = select(ImageTable)
        order_by = OrderByMetadataField("brightness", cast_to_float=False).desc().asc()

        returned_query = order_by.apply(query)

        sql = str(
            returned_query.compile(dialect=self.dialect, compile_kwargs={"literal_binds": True})
        ).lower()
        assert "order by json_extract(metadata_1.data, '$.brightness') asc" in sql

    def test_apply__cast_to_float(self) -> None:
        """Test that cast_to_float produces a CAST expression in the ORDER BY clause."""
        query = select(ImageTable)
        order_by = OrderByMetadataField("score", cast_to_float=True)

        returned_query = order_by.apply(query)

        sql = str(
            returned_query.compile(dialect=self.dialect, compile_kwargs={"literal_binds": True})
        ).lower()
        assert "order by cast(json_extract(metadata_1.data, '$.score') as float) asc" in sql


class TestOrderByEvaluationMetricField:
    dialect = DuckDBDialect()

    def test_apply_select_join__evaluation_joins(self) -> None:
        """Test that apply_select_join adds evaluation run and metric joins."""
        query = select(ImageTable)
        order_by = OrderByEvaluationMetricField("run1", "score")

        returned_query, order_value_index = order_by.apply_select_join(query)

        sql = str(
            returned_query.compile(dialect=self.dialect, compile_kwargs={"literal_binds": True})
        ).lower()
        assert "left outer join evaluation_run" in sql
        assert "left outer join evaluation_sample_metric" in sql
        assert "evaluation_sample_metric_1.metric_name = 'score'" in sql
        assert order_value_index is None

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
        assert "evaluation_sample_metric_1.metric_name = 'score'" in sql
        assert "order by evaluation_sample_metric_1.value asc" in sql

    def test_apply__descending(self) -> None:
        """Test descending ordering via desc() method."""
        query = select(ImageTable)
        order_by = OrderByEvaluationMetricField("run1", "score").desc()

        returned_query = order_by.apply(query)

        sql = str(
            returned_query.compile(dialect=self.dialect, compile_kwargs={"literal_binds": True})
        ).lower()
        assert "order by evaluation_sample_metric_1.value desc" in sql

    def test_apply__desc_then_asc(self) -> None:
        """Test that desc().asc() returns to ascending order."""
        query = select(ImageTable)
        order_by = OrderByEvaluationMetricField("run1", "score").desc().asc()

        returned_query = order_by.apply(query)

        sql = str(
            returned_query.compile(dialect=self.dialect, compile_kwargs={"literal_binds": True})
        ).lower()
        assert "order by evaluation_sample_metric_1.value asc" in sql

    def test_to_column_element__ascending(self) -> None:
        """Test that to_column_element returns only the column element without any JOIN."""
        order_by = OrderByEvaluationMetricField("run1", "score")

        col_element = order_by.to_column_element()

        sql = str(col_element.compile(compile_kwargs={"literal_binds": True})).lower()
        assert "evaluation_sample_metric_1.value asc" in sql
        assert "join" not in sql
