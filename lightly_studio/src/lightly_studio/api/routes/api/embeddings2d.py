"""Routes delivering 2D embeddings for visualization."""

from __future__ import annotations

import io
import logging
import re
import time
from typing import Union
from uuid import UUID

import pyarrow as pa
from fastapi import APIRouter, Response
from pyarrow import ipc
from pydantic import BaseModel, Field
from sqlalchemy import event
from sqlmodel import select
from typing_extensions import Annotated

from lightly_studio.db_manager import SessionDep
from lightly_studio.models.embedding_model import EmbeddingModelTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import VideoTable
from lightly_studio.resolvers import twodim_embedding_resolver
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter

embeddings2d_router = APIRouter()

Filter = Annotated[
    Union[ImageFilter, VideoFilter],
    Field(discriminator="type"),
]


class GetEmbeddings2DRequest(BaseModel):
    """Request body for retrieving 2D embeddings."""

    filters: Filter = Field(description="Filter parameters identifying matching samples")

logger = logging.getLogger(__name__)
SQL_TIMING_MIN_SECONDS = 0.01


def _enable_sql_timing(session: SessionDep) -> None:
    engine = session.get_bind()
    if engine is None:
        return
    if getattr(engine, "_lightly_sql_timing_enabled", False):
        return

    setattr(engine, "_lightly_sql_timing_enabled", True)

    @event.listens_for(engine, "before_cursor_execute")
    def _before_cursor_execute(  # type: ignore[no-untyped-def]
        conn, cursor, statement, parameters, context, executemany
    ) -> None:
        context._query_start_time = time.perf_counter()

    @event.listens_for(engine, "after_cursor_execute")
    def _after_cursor_execute(  # type: ignore[no-untyped-def]
        conn, cursor, statement, parameters, context, executemany
    ) -> None:
        start_time = getattr(context, "_query_start_time", None)
        if start_time is None:
            return
        duration = time.perf_counter() - start_time
        if duration < SQL_TIMING_MIN_SECONDS:
            return
        statement_compact = re.sub(r"IN\\s*\\([^)]*\\)", "IN (...)", statement, flags=re.IGNORECASE | re.DOTALL)
        if len(statement_compact) > 300:
            statement_compact = statement_compact[:300].rstrip() + "..."
        logger.info("sql %.3fs: %s", duration, statement_compact)


@embeddings2d_router.post("/embeddings2d/default")
def get_2d_embeddings(
    session: SessionDep,
    body: GetEmbeddings2DRequest,
) -> Response:
    """Return 2D embeddings serialized as an Arrow stream."""
    _enable_sql_timing(session)
    t0 = time.perf_counter()

    collection_id = (
        body.filters.sample_filter.collection_id if body.filters.sample_filter is not None else None
    )
    if collection_id is None:
        raise ValueError("Collection ID must be provided in filters.")

    # TODO(Malte, 09/2025): Support choosing the embedding model via API parameter.
    embedding_model = session.exec(
        select(EmbeddingModelTable)
        .where(EmbeddingModelTable.collection_id == collection_id)
        .limit(1)
    ).first()
    t1 = time.perf_counter()
    if embedding_model is None:
        raise ValueError("No embedding model configured.")

    x_array, y_array, sample_ids = twodim_embedding_resolver.get_twodim_embeddings(
        session=session,
        collection_id=collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )
    t2 = time.perf_counter()

    matching_sample_ids: set[UUID] | None = None
    filters = body.filters if body else None
    if filters:
        if not _filters_only_collection_id(filters=filters, collection_id=collection_id):
            matching_sample_ids = _get_matching_sample_ids(
                session=session,
                collection_id=collection_id,
                filters=filters,
            )
    t3 = time.perf_counter()

    if matching_sample_ids is None:
        fulfils_filter = [1] * len(sample_ids)
    else:
        fulfils_filter = [1 if sample_id in matching_sample_ids else 0 for sample_id in sample_ids]

    table = pa.table(
        {
            "x": pa.array(x_array, type=pa.float32()),
            "y": pa.array(y_array, type=pa.float32()),
            "fulfils_filter": pa.array(fulfils_filter, type=pa.uint8()),
            "sample_id": pa.array([str(sample_id) for sample_id in sample_ids], type=pa.string()),
        }
    )

    buffer = io.BytesIO()
    with ipc.new_stream(buffer, table.schema) as writer:
        writer.write_table(table)
    buffer.seek(0)
    t4 = time.perf_counter()

    logger.info(
        "embeddings2d timings: model=%.3fs twod=%.3fs filter=%.3fs arrow=%.3fs total=%.3fs",
        t1 - t0,
        t2 - t1,
        t3 - t2,
        t4 - t3,
        t4 - t0,
    )

    return Response(
        content=buffer.getvalue(),
        media_type="application/vnd.apache.arrow.stream",
        headers={
            "Content-Disposition": "inline; filename=embeddings2d.arrow",
            "Content-Type": "application/vnd.apache.arrow.stream",
            "X-Content-Type-Options": "nosniff",
        },
    )


def _get_matching_sample_ids(
    session: SessionDep,
    collection_id: UUID,
    filters: Filter,
) -> set[UUID]:
    """Get the set of sample IDs that match the given filters.

    Args:
        session: Database session.
        collection_id: Collection ID to filter by.
        filters: Filter object specifying the criteria.

    Returns:
        Set of sample IDs that match the filters.
    """
    if isinstance(filters, VideoFilter):
        query = (
            select(VideoTable.sample_id)
            .join(VideoTable.sample)
            .where(SampleTable.collection_id == collection_id)
        )
        query = filters.apply(query)
        sample_ids = session.exec(query.distinct()).all()
    else:
        query = (
            select(ImageTable.sample_id)
            .join(ImageTable.sample)
            .where(SampleTable.collection_id == collection_id)
        )
        query = filters.apply(query)
        sample_ids = session.exec(query.distinct()).all()

    return set(sample_ids)


def _filters_only_collection_id(filters: Filter, collection_id: UUID) -> bool:
    if isinstance(filters, VideoFilter):
        if (
            filters.width
            or filters.height
            or filters.fps
            or filters.duration_s
            or filters.annotation_frames_label_ids
        ):
            return False
        sample_filter = filters.sample_filter
    else:
        if filters.width or filters.height:
            return False
        sample_filter = filters.sample_filter

    if sample_filter is None or sample_filter.collection_id != collection_id:
        return False

    if (
        sample_filter.annotation_label_ids
        or sample_filter.tag_ids
        or sample_filter.metadata_filters
        or sample_filter.sample_ids
    ):
        return False

    if sample_filter.has_captions is not None:
        return False

    return True
