"""Serialize coordinates and sample IDs for saved embedding plots."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

import numpy as np
import pyarrow as pa
from numpy.typing import NDArray
from pyarrow import ipc


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
