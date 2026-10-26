"""Handler for getting cached 2D embeddings from high-dimensional embeddings."""

from __future__ import annotations

from array import array
from collections.abc import Sequence
from uuid import UUID, uuid4

import numpy as np
from lightly_mundig import TwoDimEmbedding  # type: ignore[import-untyped]
from numpy.typing import NDArray
from pyarrow import ipc
from sqlmodel import Session

from lightly_studio.database import db_insert
from lightly_studio.database.db_vector import Embedding
from lightly_studio.models.embedding_model import EmbeddingModelTable
from lightly_studio.models.embedding_plot import EmbeddingPlotTable
from lightly_studio.resolvers import embedding_plot_resolver, sample_embedding_resolver


def get_twodim_embeddings(
    session: Session,
    collection_id: UUID,
    embedding_model_id: UUID,
) -> tuple[NDArray[np.float32], NDArray[np.float32], list[UUID]]:
    """Return cached 2D embeddings together with their sample identifiers.

    Clean plots are read without loading source vectors. Missing or dirty plots are rebuilt.

    Args:
        session: Database session.
        collection_id: Collection identifier.
        embedding_model_id: Embedding model identifier.

    Returns:
        Tuple of (x coordinates, y coordinates, ordered sample IDs).
    """
    data = get_plot(
        session=session, collection_id=collection_id, embedding_model_id=embedding_model_id
    )
    table = ipc.open_stream(data).read_all()
    return (
        table["x"].to_numpy(),
        table["y"].to_numpy(),
        [UUID(value) for value in table["sample_id"].to_pylist()],
    )


def get_plot(session: Session, collection_id: UUID, embedding_model_id: UUID) -> bytes:
    """Read saved Arrow data; serialize rebuilds with embedding writes on the plot row."""
    if session.get(EmbeddingModelTable, embedding_model_id) is None:
        raise ValueError(f"Embedding model {embedding_model_id} not found.")
    key = (collection_id, embedding_model_id)
    plot = session.get(EmbeddingPlotTable, key, populate_existing=True)
    if plot is not None and not plot.is_dirty:
        return plot.data
    if plot is None:
        plot = EmbeddingPlotTable(
            collection_id=collection_id, embedding_model_id=embedding_model_id
        )
        db_insert.insert_ignoring_conflicts(
            session=session, table=EmbeddingPlotTable, rows=[plot.model_dump()]
        )
        # Publish the placeholder before rebuilding so DuckDB writers can see it.
        session.commit()
        plot = session.get(EmbeddingPlotTable, key, populate_existing=True)
        assert plot is not None
    # Hold a real write through commit: PostgreSQL writers wait; DuckDB conflicts
    # require rollback and retry. Refresh after waiting for another rebuild.
    plot.write_token = uuid4()
    session.add(plot)
    session.flush()
    session.refresh(plot)
    if plot.is_dirty:
        embeddings = sample_embedding_resolver.get_all_by_collection_id(
            session=session, collection_id=collection_id, embedding_model_id=embedding_model_id
        )
        coordinates = np.asarray(
            _calculate_2d_embeddings([embedding.embedding for embedding in embeddings]),
            dtype=np.float32,
        ).reshape(-1, 2)
        plot.data = embedding_plot_resolver.encode(
            x=coordinates[:, 0],
            y=coordinates[:, 1],
            sample_ids=[embedding.sample_id for embedding in embeddings],
        )
        plot.is_dirty = False
    data = plot.data
    session.commit()
    return data


def get_twodim_embeddings_from_axes(
    session: Session,
    collection_id: UUID,
    embedding_model_id: UUID,
    direction_x: Sequence[float],
    direction_y: Sequence[float],
) -> tuple[NDArray[np.float32], NDArray[np.float32], list[UUID]]:
    """Return 2D embeddings that are projections onto two axis directions.

    N is the number of samples with an embedding and D is the embedding dimension. The x and y
    values of a sample are the dot products of its embedding with ``direction_x`` and
    ``direction_y``. The values are not rescaled, so the spread of an axis shows how much the
    samples vary along its direction.

    The result is not stored in the database, because the directions change with each query.
    The projection runs in the database, and nothing is kept between requests.

    Args:
        session: Database session.
        collection_id: Collection identifier.
        embedding_model_id: Embedding model identifier.
        direction_x: The X axis direction of shape (D,).
        direction_y: The Y axis direction of shape (D,).

    Returns:
        Tuple of (x coordinates of shape (N,), y coordinates of shape (N,), the N sample IDs
        ordered by sample creation time).

    Raises:
        ValueError: If the embedding model does not exist, or if a direction does not have
            the embedding dimension. The projection query raises these errors.
    """
    projections = sample_embedding_resolver.get_projections_by_collection_id(
        session=session,
        collection_id=collection_id,
        embedding_model_id=embedding_model_id,
        direction_x=direction_x,
        direction_y=direction_y,
    )
    # A float32 array stores 4 bytes for each value. A list of Python floats uses about 32.
    x_values = array("f")
    y_values = array("f")
    sample_ids: list[UUID] = []
    for sample_id, x, y in projections:
        x_values.append(x)
        y_values.append(y)
        sample_ids.append(sample_id)
    return (
        np.frombuffer(x_values, dtype=np.float32),
        np.frombuffer(y_values, dtype=np.float32),
        sample_ids,
    )


def _calculate_2d_embeddings(
    embedding_values: list[Embedding],
) -> list[tuple[float, float]]:
    n_samples = len(embedding_values)
    # For 0, 1 or 2 samples we hard-code deterministic coordinates.
    if n_samples == 0:
        return []
    if n_samples == 1:
        return [(0.0, 0.0)]
    if n_samples == 2:  # noqa: PLR2004
        return [(0.0, 0.0), (1.0, 1.0)]

    embedding_calculator = TwoDimEmbedding(embedding_values)
    return embedding_calculator.calculate_2d_embedding()  # type: ignore[no-any-return]
