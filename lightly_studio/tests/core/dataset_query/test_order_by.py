from __future__ import annotations

from duckdb_engine import Dialect as DuckDBDialect
from sqlmodel import select

from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.order_by import (
    ORDER_VALUE_LABEL,
    OrderByEvaluationMetricField,
    OrderByField,
    OrderByMetadataField,
)
from lightly_studio.models.image import ImageTable


class TestOrderByField:
    def test_apply_with_order_value(self) -> None:
        """Test that apply_with_order_value appends the labeled sort column to the SELECT list."""
        query = select(ImageTable)
        order_by = OrderByField(ImageSampleField.file_name)

        returned_query = order_by.apply_with_order_value(query)

        sql = str(returned_query.compile(compile_kwargs={"literal_binds": True})).lower()
        assert "select image" in sql
        assert "image.file_name" in sql
        assert f"as {ORDER_VALUE_LABEL}" in sql

    def test_apply_joins__no_joins(self) -> None:
        """Test that apply_joins does not add JOINs for image fields."""
        query = select(ImageTable)
        order_by = OrderByField(ImageSampleField.file_name)

        returned_query = order_by.apply_joins(query)

        sql = str(returned_query.compile(compile_kwargs={"literal_binds": True})).lower()
        assert "join" not in sql

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

    # The key is bound, so it only appears as a literal under literal_binds. DuckDB reads
    # it as a one-segment JSON Pointer, hence the leading slash.
    _NUMERIC_KEY = (
        "cast(case when (cast((metadata_1.metadata_schema ->> '/brightness') as varchar)"
        " in ('integer', 'float')) then cast(metadata_1.data ->> '/brightness' as varchar) end"
        " as double precision)"
    )
    _RAW_KEY = "cast(metadata_1.data ->> '/brightness' as varchar)"

    def _compile(self, query: object) -> str:
        return str(
            query.compile(  # type: ignore[attr-defined]
                dialect=self.dialect, compile_kwargs={"literal_binds": True}
            )
        ).lower()

    def test_apply_joins__metadata_join(self) -> None:
        """Test that apply_joins adds the metadata outer join."""
        query = select(ImageTable)
        order_by = OrderByMetadataField("brightness")

        returned_query = order_by.apply_joins(query)

        assert "left outer join metadata" in self._compile(returned_query)

    def test_apply_with_order_value(self) -> None:
        """Test that the labeled order value is the numerical value of the field."""
        query = select(ImageTable)
        order_by = OrderByMetadataField("brightness")

        returned_query = order_by.apply_with_order_value(query)

        sql = self._compile(returned_query)
        assert "left outer join metadata" in sql
        assert f"{self._NUMERIC_KEY} as {ORDER_VALUE_LABEL}" in sql

    def test_apply__default_ascending(self) -> None:
        """Test that the numerical key leads and the raw value breaks ties, both ascending."""
        query = select(ImageTable)
        order_by = OrderByMetadataField("brightness")

        returned_query = order_by.apply(query)

        assert (
            f"order by {self._NUMERIC_KEY} asc nulls last, {self._RAW_KEY} asc nulls last"
            in self._compile(returned_query)
        )

    def test_apply__descending(self) -> None:
        """Test that desc() applies to every sort key, not just the first."""
        query = select(ImageTable)
        order_by = OrderByMetadataField("brightness").desc()

        returned_query = order_by.apply(query)

        assert (
            f"order by {self._NUMERIC_KEY} desc nulls last, {self._RAW_KEY} desc nulls last"
            in self._compile(returned_query)
        )

    def test_apply__desc_then_asc(self) -> None:
        """Test that desc().asc() returns to ascending order."""
        query = select(ImageTable)
        order_by = OrderByMetadataField("brightness").desc().asc()

        returned_query = order_by.apply(query)

        assert (
            f"order by {self._NUMERIC_KEY} asc nulls last, {self._RAW_KEY} asc nulls last"
            in self._compile(returned_query)
        )

    def test_apply__cast_wraps_the_case(self) -> None:
        """Test that the cast is applied to the CASE result, not inside a branch.

        A non-numerical value must never reach the cast, whatever order the engine
        chooses to evaluate in.
        """
        query = select(ImageTable)
        order_by = OrderByMetadataField("brightness")

        returned_query = order_by.apply(query)

        sql = self._compile(returned_query)
        assert "cast(case when" in sql
        assert "case when" not in sql.replace("cast(case when", "")

    def test_to_column_elements__two_keys(self) -> None:
        """Test that a metadata sort contributes both keys, without any JOIN."""
        order_by = OrderByMetadataField("brightness")

        elements = order_by.to_column_elements()

        assert len(elements) == 2
        sql = " ".join(
            str(element.compile(dialect=self.dialect, compile_kwargs={"literal_binds": True}))
            for element in elements
        ).lower()
        assert "join" not in sql


class TestOrderByEvaluationMetricField:
    dialect = DuckDBDialect()

    def test_apply_joins__evaluation_joins(self) -> None:
        """Test that apply_joins adds evaluation run and metric joins."""
        query = select(ImageTable)
        order_by = OrderByEvaluationMetricField("run1", "score")

        returned_query = order_by.apply_joins(query)

        sql = str(
            returned_query.compile(dialect=self.dialect, compile_kwargs={"literal_binds": True})
        ).lower()
        assert "left outer join evaluation_run" in sql
        assert "left outer join evaluation_sample_metric" in sql
        assert "evaluation_sample_metric_1.metric_name = 'score'" in sql

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

    def test_to_column_elements__ascending(self) -> None:
        """Test that to_column_elements returns only the column element without any JOIN."""
        order_by = OrderByEvaluationMetricField("run1", "score")

        (col_element,) = order_by.to_column_elements()

        sql = str(col_element.compile(compile_kwargs={"literal_binds": True})).lower()
        assert "evaluation_sample_metric_1.value asc" in sql
        assert "join" not in sql
