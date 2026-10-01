"""Tests for generic metadata filters."""

import pytest
import sqlmodel
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql

from lightly_studio.models.metadata import SampleMetadataTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers.metadata_resolver import metadata_filter
from lightly_studio.resolvers.metadata_resolver.metadata_filter import MetadataFilter


@pytest.mark.parametrize(
    "value",
    [[], ["Zurich", True], [1, 2], [None, 1]],
)
def test_metadata_filter__invalid_in_value(value: list[object]) -> None:
    with pytest.raises(ValidationError):
        MetadataFilter(key="city", op="in", value=value)


@pytest.mark.parametrize(
    "value",
    [["Zurich", "Berlin"], [True, False], ["Zurich", None], [None]],
)
def test_metadata_filter__valid_in_value(value: list[object]) -> None:
    metadata_filter = MetadataFilter(key="city", op="in", value=value)

    assert metadata_filter.value == value


def test_apply_metadata_filters__postgres_missing_and_special_key() -> None:
    query = metadata_filter.apply_metadata_filters(
        sqlmodel.select(SampleTable),
        [MetadataFilter(key="city.name's", op="in", value=["Zurich", None])],
        metadata_model=SampleMetadataTable,
        metadata_join_condition=sqlmodel.col(SampleMetadataTable.sample_id)
        == sqlmodel.col(SampleTable.sample_id),
    )

    compiled = query.compile(dialect=postgresql.dialect())  # type: ignore[no-untyped-call]
    sql = str(compiled).lower()
    assert "left outer join" in sql
    assert "->>" in sql
    assert " in " in sql
    assert " is null" in sql
    assert "city.name's" in compiled.params.values()
