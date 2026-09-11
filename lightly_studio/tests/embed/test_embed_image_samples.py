"""Image ingestion through the embedding registry."""

from uuid import uuid4

import numpy as np
import pytest
from lightly_studio_serve.types import EmbeddingResult
from pytest_mock import MockerFixture
from sqlmodel import Session, select

from lightly_studio.embed import embed_samples, embedder_registry
from lightly_studio.embed.embedder_registry import EmbedderRegistry
from lightly_studio.embed.random_embedder import RandomEmbedder
from lightly_studio.models.collection import SampleType
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from tests.helpers_resolvers import ImageStub, create_collection, create_image, create_images


@pytest.fixture
def image_embedder(mocker: MockerFixture) -> RandomEmbedder:
    registry = EmbedderRegistry()
    embedder = RandomEmbedder()
    registry.register(embedder=embedder)
    mocker.patch.object(embedder_registry, "_registry", registry)
    mocker.patch.object(embedder_registry, "_load_builtin_embedder", return_value=None)
    return embedder


@pytest.mark.parametrize("kept_indices", [[0, 1], [1], []])
def test_embed_image_samples(
    db_session: Session,
    image_embedder: RandomEmbedder,
    mocker: MockerFixture,
    kept_indices: list[int],
) -> None:
    collection = create_collection(session=db_session)
    images = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="/a.jpg"), ImageStub(path="/b.jpg")],
    )
    sample_ids = [image.sample_id for image in reversed(images)]
    vectors = np.array([[index, 2, 3] for index in kept_indices], dtype=np.float32).reshape(-1, 3)
    embed = mocker.patch.object(
        type(image_embedder),
        "embed_images",
        return_value=EmbeddingResult(embeddings=vectors, kept_indices=kept_indices),
    )
    embed_samples.embed_image_samples(
        session=db_session, collection_id=collection.collection_id, sample_ids=sample_ids
    )
    embed.assert_called_once_with(paths=["/b.jpg", "/a.jpg"])
    model = embed_samples._get_default_model(
        session=db_session, collection_id=collection.collection_id
    )
    assert model is not None
    assert model.name == "random_model"
    rows = db_session.exec(select(SampleEmbeddingTable)).all()
    assert {row.sample_id for row in rows} == {sample_ids[index] for index in kept_indices}
    for row in rows:
        assert row.embedding_model_id == model.embedding_model_id
        np.testing.assert_array_equal(row.embedding, [sample_ids.index(row.sample_id), 2, 3])


@pytest.mark.parametrize(
    "case", ["missing_collection", "wrong_type", "empty", "missing_id", "foreign_id"]
)
def test_embed_image_samples__guards(
    db_session: Session, image_embedder: RandomEmbedder, mocker: MockerFixture, case: str
) -> None:
    collection = create_collection(
        session=db_session,
        sample_type=SampleType.VIDEO if case == "wrong_type" else SampleType.IMAGE,
    )
    collection_id = uuid4() if case == "missing_collection" else collection.collection_id
    sample_ids = [] if case == "empty" else [uuid4()]
    if case == "foreign_id":
        other = create_collection(session=db_session, collection_name="other")
        sample_ids = [create_image(session=db_session, collection_id=other.collection_id).sample_id]
    embed = mocker.spy(type(image_embedder), "embed_images")
    resolve = mocker.spy(embedder_registry.get_registry(), "get_image_path_embedder")
    if case == "empty":
        embed_samples.embed_image_samples(
            session=db_session, collection_id=collection_id, sample_ids=sample_ids
        )
    else:
        with pytest.raises(ValueError, match=r"not found|requires an image collection|must belong"):
            embed_samples.embed_image_samples(
                session=db_session, collection_id=collection_id, sample_ids=sample_ids
            )
    embed.assert_not_called()
    resolve.assert_not_called()
    assert (
        embed_samples._get_default_model(session=db_session, collection_id=collection.collection_id)
        is None
    )


@pytest.mark.usefixtures("image_embedder")
def test_embed_image_samples__unavailable(
    db_session: Session, mocker: MockerFixture, caplog: pytest.LogCaptureFixture
) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    mocker.patch.object(
        embedder_registry.get_registry(), "get_image_path_embedder", return_value=None
    )
    embed_samples.embed_image_samples(
        session=db_session, collection_id=collection.collection_id, sample_ids=[image.sample_id]
    )
    assert "Skipping embedding generation" in caplog.text
    assert list(db_session.exec(select(SampleEmbeddingTable)).all()) == []
    assert (
        embed_samples._get_default_model(session=db_session, collection_id=collection.collection_id)
        is None
    )


@pytest.mark.parametrize(
    ("indices", "rows"), [([-1], 1), ([2], 1), ([0, 0], 2), ([1, 0], 2), ([0], 2), ([], 1)]
)
def test_embed_image_samples__invalid_result(
    db_session: Session,
    image_embedder: RandomEmbedder,
    mocker: MockerFixture,
    indices: list[int],
    rows: int,
) -> None:
    collection = create_collection(session=db_session)
    images = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="/a.jpg"), ImageStub(path="/b.jpg")],
    )
    mocker.patch.object(
        type(image_embedder),
        "embed_images",
        return_value=EmbeddingResult(
            embeddings=np.zeros((rows, 3), dtype=np.float32), kept_indices=indices
        ),
    )
    with pytest.raises(ValueError, match=r"indices|Number of embeddings"):
        embed_samples.embed_image_samples(
            session=db_session,
            collection_id=collection.collection_id,
            sample_ids=[image.sample_id for image in images],
        )
    assert list(db_session.exec(select(SampleEmbeddingTable)).all()) == []
