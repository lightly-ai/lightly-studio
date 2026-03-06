"""Benchmark for the VideoFrame N+1 query problem on the ``video`` relationship.

Background
----------
The ``POST /collections/{id}/frame/`` endpoint calls
``video_frame_resolver.get_all_by_collection_id()``, which previously returned
``VideoFrameTable`` rows without eagerly loading the ``VideoFrameTable.video``
relationship.  Every subsequent call to ``vf.video`` inside
``_build_video_frame_view()`` therefore triggered a separate lazy SELECT, one
per unique video in the page.

For a dataset with one video per frame (e.g. 100 k 1-second clips) this
becomes a true N+1 problem.

Worst-case query count (BEFORE fix) for 20 distinct videos, 100 frames:
------------------------------------------------------------------------
- 1 x SELECT COUNT(*)   (total-count subquery)
- 1 x SELECT video_frame (main paginated query)
- 1 x SELECT sample      (selectinload for VideoFrameTable.sample)
- 1 x SELECT annotation  (selectinload for SampleTable.annotations)
- 20 x SELECT video      (one lazy SELECT per unique video)

Total ~24 round-trips for 20 videos.

AFTER fix
---------
``_get_load_options()`` now includes ``selectinload(VideoFrameTable.video)``,
which batches all video look-ups into a single IN-query.

Total ~4-5 round-trips regardless of the number of unique videos.
"""

from __future__ import annotations

import time
from collections.abc import Generator
from typing import Any

import pytest
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import video_frame_resolver
from tests.helpers_resolvers import create_collection
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames

NUM_VIDEOS = 20
FRAMES_PER_VIDEO = 5
TOTAL_FRAMES = NUM_VIDEOS * FRAMES_PER_VIDEO


@pytest.fixture
def benchmark_session() -> Generator[tuple[Session, Any], None, None]:
    """Yield a (session, engine) pair backed by an in-memory DuckDB database."""
    engine = create_engine("duckdb:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session, engine


def _count_select_statements(engine: Any) -> list[str]:
    """Return a mutable list that accumulates every SQL statement executed.

    Attaches a ``before_cursor_execute`` listener to *engine* and returns the
    list so callers can inspect it after the queries run.
    """
    statements: list[str] = []

    @event.listens_for(engine, "before_cursor_execute")
    def _on_execute(*args: Any, **kwargs: Any) -> None:  # noqa: ARG001
        statements.append(args[2])  # args[2] is the SQL statement string

    return statements


def test_video_frame_n1_benchmark(
    benchmark_session: tuple[Session, Any],
) -> None:
    """Verify that ``get_all_by_collection_id`` does not cause N+1 queries.

    The test:
    1. Inserts 20 distinct videos with 5 frames each (100 frames total).
    2. Records every SQL statement issued during a single call to
       ``get_all_by_collection_id``.
    3. Asserts that the total number of SELECT statements is well below the
       N+1 worst-case (NUM_VIDEOS + fixed overhead ≈ 24), proving that the
       eager-load fix is in effect.
    """
    session, engine = benchmark_session

    # ------------------------------------------------------------------ setup
    collection = create_collection(session=session, sample_type=SampleType.VIDEO)
    video_frames_collection_id = None

    for i in range(NUM_VIDEOS):
        result = create_video_with_frames(
            session=session,
            collection_id=collection.collection_id,
            video=VideoStub(
                path=f"/videos/clip_{i:03d}.mp4",
                duration_s=float(FRAMES_PER_VIDEO),
                fps=1.0,
            ),
        )
        video_frames_collection_id = result.video_frames_collection_id

    assert video_frames_collection_id is not None

    # ------------------------------------------------------------------ measure
    statements = _count_select_statements(engine)

    start = time.perf_counter()
    result = video_frame_resolver.get_all_by_collection_id(
        session=session,
        collection_id=video_frames_collection_id,
        pagination=Paginated(offset=0, limit=TOTAL_FRAMES),
    )
    elapsed_s = time.perf_counter() - start

    # ------------------------------------------------------------------ assert
    assert len(result.samples) == TOTAL_FRAMES, (
        f"Expected {TOTAL_FRAMES} frames, got {len(result.samples)}"
    )

    select_count = sum(1 for s in statements if s.lstrip().upper().startswith("SELECT"))

    # Before the fix the count would be NUM_VIDEOS + fixed ≈ 24.
    # After the fix a single selectinload replaces the N lazy selects,
    # so the count must be well below NUM_VIDEOS.
    assert select_count < NUM_VIDEOS, (
        f"N+1 regression detected: {select_count} SELECT statements issued "
        f"(threshold < {NUM_VIDEOS}). "
        f"Wall-clock time: {elapsed_s:.3f}s. "
        "Ensure selectinload(VideoFrameTable.video) is in _get_load_options()."
    )
