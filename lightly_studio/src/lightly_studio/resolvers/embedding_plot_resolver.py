"""Serialize coordinates and sample IDs for saved embedding plots."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID, uuid4

import numpy as np
import pyarrow as pa
from numpy.typing import NDArray
from pyarrow import ipc
from sqlmodel import Session, col, select, update

from lightly_studio.models.embedding_plot import EmbeddingPlotTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.utils import batching


def mark_dirty(session: Session, sample_ids: Sequence[UUID]) -> None:
    """Invalidate every model's plot in affected collections without committing."""
    for batch in batching.batched(items=sample_ids):
        collection_ids = select(SampleTable.collection_id).where(
            col(SampleTable.sample_id).in_(batch)
        )
        # Change the token even for dirty plots so concurrent rebuilds conflict with writes.
        # Disable ORM synchronization: DuckDB UPDATE RETURNING can skip conflicting writes.
        session.exec(
            update(EmbeddingPlotTable)
            .where(col(EmbeddingPlotTable.collection_id).in_(collection_ids))
            .values(is_dirty=True, write_token=uuid4())
            .execution_options(synchronize_session=False)
        )


def encode(
    x: Sequence[float] | NDArray[np.float32],
    y: Sequence[float] | NDArray[np.float32],
    sample_ids: Sequence[UUID],
) -> bytes:
    """Serialize aligned coordinates and IDs; Arrow rejects unequal column lengths."""
    table = pa.table(
        {
            "x": pa.array(x, type=pa.float32()),
            "y": pa.array(y, type=pa.float32()),
            "sample_id": pa.array([str(sample_id) for sample_id in sample_ids], type=pa.string()),
        }
    )
    buffer = pa.BufferOutputStream()
    with ipc.new_stream(buffer, table.schema) as writer:
        writer.write_table(table)
    return bytes(buffer.getvalue())
