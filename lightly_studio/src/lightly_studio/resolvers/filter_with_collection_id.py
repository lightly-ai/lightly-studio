"""Generic filter type that carries a collection ID alongside filters."""

from __future__ import annotations

from typing import Any, Generic, Protocol, TypeVar, cast, runtime_checkable
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlmodel import col
from typing_extensions import Self

from lightly_studio.models.sample import SampleTable


class QueryWithWhereProtocol(Protocol):
    """Structural type for query objects that support .where()."""

    def where(self, *args: Any, **kwargs: Any) -> Self:
        """Add a WHERE clause and return the same query type."""
        ...


Q = TypeVar("Q", bound=QueryWithWhereProtocol)


@runtime_checkable
class FilterProtocol(Protocol):
    """Structural type for filters that have an apply method."""

    def apply(self, query: Any) -> Any:
        """Apply this filter to the query."""
        ...


T = TypeVar("T", bound=FilterProtocol)


class FilterWithCollectionId(BaseModel, Generic[T]):
    """Pairs a collection ID with a filter."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    collection_id: UUID
    filter: T

    def apply(
        self,
        query: Q,
        sample_table: type[SampleTable] = SampleTable,
    ) -> Q:
        """Apply collection scope then the inner filter to the query."""
        scoped = query.where(col(sample_table.collection_id) == self.collection_id)
        return cast(Q, self.filter.apply(scoped))
