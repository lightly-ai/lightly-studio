"""Generic filter type that carries a collection ID alongside filters."""

from __future__ import annotations

from typing import Generic, Protocol, TypeVar, runtime_checkable
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlmodel import col

from lightly_studio.models.sample import SampleTable
from lightly_studio.type_definitions import QueryType


@runtime_checkable
class FilterProtocol(Protocol):
    """Structural type for filters that have an apply method."""

    def apply(self, query: QueryType) -> QueryType:
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
        query: QueryType,
    ) -> QueryType:
        """Apply collection scope then the inner filter to the query.

        Args:
            query: The query to filter.
        """
        scoped = query.where(col(SampleTable.collection_id) == self.collection_id)
        return self.filter.apply(scoped)
