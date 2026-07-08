"""Mixin for filtering a query by embedding-region sample ids."""

from __future__ import annotations

from uuid import UUID

import sqlalchemy
from pydantic import BaseModel
from sqlalchemy.orm import Mapped

from lightly_studio.database import db_array
from lightly_studio.models.embedding_region import EmbeddingRegion
from lightly_studio.type_definitions import QueryType


class RegionSampleIdsFilter(BaseModel):
    """Mixin adding embedding-region sample-id filtering to a filter."""

    embedding_region: EmbeddingRegion | None = None

    # Sample ids enclosed by ``embedding_region``, resolved server-side.
    # ``None`` means no region filter; an empty list matches nothing.
    region_sample_ids: list[UUID] | None = None

    def _apply_region_sample_ids_filter(
        self,
        query: QueryType,
        sample_id_column: Mapped[UUID],
    ) -> QueryType:
        """Filter ``query`` by the region-enclosed sample ids on the given column."""
        if self.region_sample_ids is None:
            return query
        # An empty region encloses no points and must match nothing (not everything).
        if not self.region_sample_ids:
            return query.where(sqlalchemy.false())
        return query.where(
            db_array.in_array(column=sample_id_column, values=self.region_sample_ids)
        )
