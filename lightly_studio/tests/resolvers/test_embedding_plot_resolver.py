"""Saved plot serialization and database storage tests."""

import importlib
from uuid import uuid4

import numpy as np
import pyarrow as pa
import pytest
from pyarrow import ipc
from sqlmodel import Session, select

from lightly_studio.models.embedding_plot import EmbeddingPlotTable
from lightly_studio.models.sample_embedding import SampleEmbeddingCreate, SampleEmbeddingTable
from lightly_studio.resolvers import (
    dataset_resolver,
    embedding_plot_resolver,
    sample_embedding_resolver,
)
from tests.helpers_resolvers import create_collection, create_embedding_model, create_image


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


@pytest.mark.parametrize(
    "operation", ["single", "batch", "mixed", "rollback", "empty", "duplicate"]
)
def test_mark_dirty__embedding_writes(db_session: Session, operation: str) -> None:
    collection = create_collection(session=db_session)
    model, other_model = [
        create_embedding_model(
            session=db_session,
            collection_id=collection.collection_id,
            embedding_model_name=name,
            embedding_dimension=2,
        )
        for name in ["first", "second"]
    ]
    sample = create_image(session=db_session, collection_id=collection.collection_id)
    embedding = SampleEmbeddingCreate(
        sample_id=sample.sample_id,
        embedding_model_id=model.embedding_model_id,
        embedding=np.array([1.0, 2.0], dtype=np.float32),
    )
    if operation == "duplicate":
        sample_embedding_resolver.create(session=db_session, sample_embedding=embedding)
    plots = [
        EmbeddingPlotTable(collection_id=collection_id, embedding_model_id=model_id, is_dirty=False)
        for collection_id, model_id in [
            (collection.collection_id, model.embedding_model_id),
            (collection.collection_id, other_model.embedding_model_id),
            (uuid4(), uuid4()),
        ]
    ]
    tokens = [plot.write_token for plot in plots]
    plots = [db_session.merge(plot) for plot in plots]
    db_session.commit()
    if operation == "single":
        sample_embedding_resolver.create(session=db_session, sample_embedding=embedding)
    elif operation == "empty":
        sample_embedding_resolver.create_many(session=db_session, sample_embeddings=[])
    else:
        embeddings = [embedding]
        if operation == "mixed":
            other_id = other_model.embedding_model_id
            embeddings.append(embedding.model_copy(update={"embedding_model_id": other_id}))
        sample_embedding_resolver.create_many(
            session=db_session, sample_embeddings=embeddings, commit=False
        )
        if operation == "rollback":
            db_session.rollback()
        else:
            db_session.commit()
    db_session.expire_all()
    dirty = operation in ("single", "batch", "mixed", "duplicate")
    expected = [dirty, operation == "mixed", False]
    assert [plot.is_dirty for plot in plots] == expected
    assert [plot.write_token != token for plot, token in zip(plots, tokens)] == expected
    saved = db_session.get(SampleEmbeddingTable, (sample.sample_id, model.embedding_model_id))
    assert (saved is not None) == dirty


def test_embedding_plot__dataset_cleanup(db_session: Session) -> None:
    use_postgres = db_session.get_bind().dialect.name == "postgresql"
    collection = create_collection(session=db_session)
    child = create_collection(session=db_session, parent_collection_id=collection.collection_id)
    plots = [
        EmbeddingPlotTable(collection_id=c.collection_id, embedding_model_id=uuid4())
        for c in (collection, child)
    ]
    retained = EmbeddingPlotTable(collection_id=uuid4(), embedding_model_id=uuid4())
    db_session.add_all([*plots, retained])
    db_session.commit()
    if use_postgres:
        dataset_resolver.deep_copy(
            session=db_session, dataset_id=collection.dataset_id, copy_name="copy"
        )
        assert len(db_session.exec(select(EmbeddingPlotTable)).all()) == 3
    keys = [(plot.collection_id, plot.embedding_model_id) for plot in plots]
    retained_key = (retained.collection_id, retained.embedding_model_id)
    if use_postgres:
        dataset_resolver.delete_dataset(session=db_session, dataset_id=collection.dataset_id)
    else:
        # The package exports a function with the same name as this module.
        module = importlib.import_module("lightly_studio.resolvers.dataset_resolver.delete_dataset")
        module._delete_sample_embeddings(session=db_session, dataset_id=collection.dataset_id)
        db_session.commit()
    assert all(db_session.get(EmbeddingPlotTable, key) is None for key in keys)
    assert db_session.get(EmbeddingPlotTable, retained_key) is not None


def test_mark_dirty__already_dirty(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    sample = create_image(session=db_session, collection_id=collection.collection_id)
    plot = EmbeddingPlotTable(collection_id=collection.collection_id, embedding_model_id=uuid4())
    db_session.add(plot)
    db_session.commit()
    old_token = plot.write_token
    embedding_plot_resolver.mark_dirty(session=db_session, sample_ids=[sample.sample_id])
    db_session.commit()
    db_session.refresh(plot)
    assert plot.is_dirty is True
    assert plot.write_token != old_token
