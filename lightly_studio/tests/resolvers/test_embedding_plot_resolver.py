"""Saved plot serialization and database storage tests."""

from uuid import uuid4

import pyarrow as pa
import pytest
from pyarrow import ipc
from sqlmodel import Session

from lightly_studio.models.embedding_plot import EmbeddingPlotTable
from lightly_studio.resolvers import embedding_plot_resolver


@pytest.mark.parametrize("count", [0, 2])
def test_encode__round_trip(count: int) -> None:
    sample_ids = [uuid4() for _ in range(count)]
    data = embedding_plot_resolver.encode(
        x=[1.0, -2.0][:count], y=[3.0, 4.0][:count], sample_ids=sample_ids
    )
    table = ipc.open_stream(data).read_all()
    assert table.schema == pa.schema(
        [("x", pa.float32()), ("y", pa.float32()), ("sample_id", pa.string())]
    )
    assert table.to_pydict() == {
        "x": [1.0, -2.0][:count],
        "y": [3.0, 4.0][:count],
        "sample_id": [str(sample_id) for sample_id in sample_ids],
    }


@pytest.mark.parametrize(("x", "y", "ids"), [(1, 0, 1), (1, 1, 0)])
def test_encode__unequal_lengths(x: int, y: int, ids: int) -> None:
    with pytest.raises(pa.ArrowInvalid, match="length"):
        embedding_plot_resolver.encode(x=[1.0] * x, y=[2.0] * y, sample_ids=[uuid4()] * ids)


def test_embedding_plot__storage(db_session: Session) -> None:
    collection_id, model_id = uuid4(), uuid4()
    sample_ids = [uuid4()]
    data = embedding_plot_resolver.encode(x=[1.0], y=[2.0], sample_ids=sample_ids)
    plots = [
        EmbeddingPlotTable(collection_id=collection_id, embedding_model_id=model_id, data=data),
        EmbeddingPlotTable(collection_id=collection_id, embedding_model_id=uuid4()),
        EmbeddingPlotTable(collection_id=uuid4(), embedding_model_id=model_id),
    ]
    assert len({plot.write_token for plot in plots}) == 3
    write_token = plots[0].write_token
    db_session.add_all(plots)
    db_session.commit()
    db_session.expunge_all()
    saved = db_session.get(EmbeddingPlotTable, (collection_id, model_id))
    assert saved is not None
    assert saved.is_dirty is True
    assert saved.write_token == write_token
    assert saved.data == data
    assert ipc.open_stream(saved.data).read_all()["sample_id"].to_pylist() == [str(sample_ids[0])]
