"""Tests for the dataset-level embedding functions."""

from __future__ import annotations

import logging
from uuid import UUID

import numpy as np
import pytest
from lightly_studio_serve.embedder import ImageCropPathEmbedder, ImagePathEmbedder
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec, ImageCrop
from pytest_mock import MockerFixture
from sqlmodel import Session, select

from lightly_studio.embed import default_embedder, embed_dataset, embed_samples, embedder_registry
from lightly_studio.embed.embedder_registry import EmbedderRegistry
from lightly_studio.embed.random_embedder import RandomEmbedder
from lightly_studio.models.collection import SampleType
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.resolvers import (
    collection_embedding_model_resolver,
    collection_resolver,
    image_resolver,
    sample_embedding_resolver,
)
from tests.helpers_resolvers import (
    ImageStub,
    create_annotation,
    create_annotation_label,
    create_collection,
    create_embedding_model,
    create_image,
    create_images,
)

_RANDOM_EMBEDDING_DIMENSION = 3


class _FailOnCallEmbedder(ImagePathEmbedder):
    """Embeds paths as zeros and raises on a known call, as a failing embedder does.

    Shares the random model's space so it resolves as the collection's default.
    """

    __slots__ = ("_call_count", "_fail_on_call")

    def __init__(self, fail_on_call: int) -> None:
        self._call_count = 0
        self._fail_on_call = fail_on_call

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        """Describe the shared random embedding space with dimension 3."""
        return EmbeddingSpaceSpec(space_key="random_model", dimension=3)

    def embed_images(self, paths: list[str]) -> EmbeddingResult:
        """Embed every path as zeros, or raise on call number ``fail_on_call``."""
        self._call_count += 1
        if self._call_count == self._fail_on_call:
            raise RuntimeError("The embedder failed.")
        return EmbeddingResult(
            embeddings=np.zeros((len(paths), 3), dtype=np.float32),
            kept_indices=list(range(len(paths))),
        )


class _BoxXImageCropEmbedder(ImageCropPathEmbedder):
    """Embeds each crop as its left edge x and drops the last crop.

    Deriving the vector from the crop's box, not the input position, makes the test fail
    if ``embed_annotation_collection`` matches crops to the wrong annotation IDs. A dropped
    input verifies that only kept embeddings are stored. Shares the random model's space so
    it resolves as the collection's default.
    """

    __slots__ = ()

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        """Describe the shared random embedding space with dimension 3."""
        return EmbeddingSpaceSpec(space_key="random_model", dimension=3)

    def embed_image_crops(self, crops: list[ImageCrop]) -> EmbeddingResult:
        """Embed all crops but the last as [x, x, x], read from the crop's left edge."""
        kept_indices = list(range(len(crops) - 1))
        embeddings = np.array([[crops[index].x] * 3 for index in kept_indices], dtype=np.float32)
        return EmbeddingResult(embeddings=embeddings, kept_indices=kept_indices)


@pytest.fixture
def patched_registry(mocker: MockerFixture) -> EmbedderRegistry:
    """Route embedding to a fresh registry so tests never touch the shared singleton."""
    registry = EmbedderRegistry()
    registry.register(embedder=RandomEmbedder(dimension=_RANDOM_EMBEDDING_DIMENSION))
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)
    return registry


@pytest.mark.usefixtures("patched_registry")
def test_embed_missing_images(db_session: Session) -> None:
    """Images are stored under the collection's default model, embedded by the registry."""
    collection = create_collection(session=db_session)
    create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="/test/a.jpg"), ImageStub(path="/test/b.jpg")],
    )
    model_id = _register_default_random_model(
        session=db_session, collection_id=collection.collection_id
    )

    stored = embed_dataset.embed_missing_images(
        session=db_session, collection_id=collection.collection_id
    )

    assert stored == 2
    count = sample_embedding_resolver.get_embedding_count(
        session=db_session, collection_id=collection.collection_id, embedding_model_id=model_id
    )
    assert count == 2


@pytest.mark.usefixtures("patched_registry")
def test_embed_missing_images__skips_embedded_images(db_session: Session) -> None:
    """Only images without an embedding of the default model are embedded."""
    collection = create_collection(session=db_session)
    create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="/test/a.jpg"), ImageStub(path="/test/b.jpg")],
    )
    _register_default_random_model(session=db_session, collection_id=collection.collection_id)
    assert (
        embed_dataset.embed_missing_images(
            session=db_session, collection_id=collection.collection_id
        )
        == 2
    )
    create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="/test/c.jpg")],
    )

    stored = embed_dataset.embed_missing_images(
        session=db_session, collection_id=collection.collection_id
    )

    assert stored == 1
    assert len(_stored_embeddings(session=db_session)) == 3


def test_embed_missing_images__failure_keeps_earlier_chunks(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    """An embedder failure on a chunk keeps the embeddings of the chunks before it."""
    collection = create_collection(session=db_session)
    images = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path=f"/test/{index}.jpg") for index in range(5)],
    )
    model_id = _register_default_random_model(
        session=db_session, collection_id=collection.collection_id
    )
    # The chunks are [0, 1], [2, 3] and [4]. The embedder fails on the third chunk.
    mocker.patch.object(embed_dataset, "_IMAGE_EMBED_BATCH_SIZE", 2)
    registry = EmbedderRegistry()
    registry.register(embedder=_FailOnCallEmbedder(fail_on_call=3))
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)

    with pytest.raises(RuntimeError, match="The embedder failed"):
        embed_dataset.embed_missing_images(
            session=db_session, collection_id=collection.collection_id
        )

    db_session.rollback()
    sample_ids = [image.sample_id for image in images]
    rows = sample_embedding_resolver.get_by_sample_ids(
        session=db_session, sample_ids=sample_ids, embedding_model_id=model_id
    )
    # Images are selected ordered by path, which is the creation order here.
    assert {row.sample_id for row in rows} == set(sample_ids[:4])


@pytest.mark.usefixtures("patched_registry")
def test_embed_missing_images__no_default_embeds_all_and_registers(
    db_session: Session,
) -> None:
    """With no default model, the registry's image embedder is used and set as default."""
    collection = create_collection(session=db_session)
    create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path=f"/test/{name}.jpg") for name in ("a", "b", "c")],
    )

    stored = embed_dataset.embed_missing_images(
        session=db_session, collection_id=collection.collection_id
    )

    assert stored == 3
    model_id = collection_embedding_model_resolver.get_default_by_collection_id(
        session=db_session, collection_id=collection.collection_id
    )
    assert model_id is not None
    count = sample_embedding_resolver.get_embedding_count(
        session=db_session, collection_id=collection.collection_id, embedding_model_id=model_id
    )
    assert count == 3


@pytest.mark.usefixtures("patched_registry")
def test_embed_missing_images__no_images_registers_no_default(db_session: Session) -> None:
    """A collection without images gets no default model."""
    collection = create_collection(session=db_session)

    stored = embed_dataset.embed_missing_images(
        session=db_session, collection_id=collection.collection_id
    )

    assert stored == 0
    model_id = collection_embedding_model_resolver.get_default_by_collection_id(
        session=db_session, collection_id=collection.collection_id
    )
    assert model_id is None


@pytest.mark.usefixtures("patched_registry")
def test_embed_missing_images__nothing_missing_does_not_resolve(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    """When every image has an embedding, the embedder is not resolved."""
    collection = create_collection(session=db_session)
    create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="/test/a.jpg"), ImageStub(path="/test/b.jpg")],
    )
    assert (
        embed_dataset.embed_missing_images(
            session=db_session, collection_id=collection.collection_id
        )
        == 2
    )
    spy = mocker.spy(default_embedder, "resolve_default_embedder")

    stored = embed_dataset.embed_missing_images(
        session=db_session, collection_id=collection.collection_id
    )

    assert stored == 0
    spy.assert_not_called()


@pytest.mark.usefixtures("patched_registry")
def test_embed_missing_images__fetches_paths_per_chunk(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    """Each chunk fetches only its own image paths."""
    collection = create_collection(session=db_session)
    create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path=f"/test/{index}.jpg") for index in range(5)],
    )
    mocker.patch.object(embed_dataset, "_IMAGE_EMBED_BATCH_SIZE", 2)
    spy = mocker.spy(image_resolver, "get_many_by_id")

    stored = embed_dataset.embed_missing_images(
        session=db_session, collection_id=collection.collection_id
    )

    assert stored == 5
    assert [len(call.kwargs["sample_ids"]) for call in spy.call_args_list] == [2, 2, 1]


def test_embed_missing_images__no_registered_embedder_returns_none(
    db_session: Session,
    mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """With a default model but no embedder for its space, embedding is skipped."""
    collection = create_collection(session=db_session)
    create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="/test/a.jpg"), ImageStub(path="/test/b.jpg")],
    )
    _register_default_random_model(session=db_session, collection_id=collection.collection_id)
    # An empty registry cannot supply an embedder for the default model's space.
    mocker.patch.object(embedder_registry, "get_registry", return_value=EmbedderRegistry())

    with caplog.at_level(level=logging.WARNING):
        stored = embed_dataset.embed_missing_images(
            session=db_session, collection_id=collection.collection_id
        )

    assert stored is None
    assert "No embedding model loaded" in caplog.text
    assert _stored_embeddings(session=db_session) == []


@pytest.mark.usefixtures("patched_registry")
def test_embed_missing_images__enables_text_query(db_session: Session) -> None:
    """After the image embed registers a default, a text query resolves the same model."""
    collection = create_collection(session=db_session)
    create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="/test/a.jpg"), ImageStub(path="/test/b.jpg")],
    )

    embed_dataset.embed_missing_images(session=db_session, collection_id=collection.collection_id)

    # The registry serves the text query with the default the image embed just registered.
    embedding = embed_samples.embed_text_for_collection(
        session=db_session, collection_id=collection.collection_id, text="a red car"
    )
    assert len(embedding) == _RANDOM_EMBEDDING_DIMENSION


@pytest.mark.usefixtures("patched_registry")
def test_embed_annotation_collection(
    db_session: Session,
) -> None:
    """Annotation crops are stored under the collection's default model, via the registry."""
    annotation_collection_id = _create_annotation_collection(session=db_session)
    model_id = _register_default_random_model(
        session=db_session, collection_id=annotation_collection_id
    )

    embed_dataset.embed_annotation_collection(
        session=db_session, annotation_collection_id=annotation_collection_id
    )

    count = sample_embedding_resolver.get_embedding_count(
        session=db_session, collection_id=annotation_collection_id, embedding_model_id=model_id
    )
    assert count == 1


@pytest.mark.usefixtures("patched_registry")
def test_embed_annotation_collection__no_default_registers_registry_default(
    db_session: Session,
) -> None:
    """With no default model, the registry's crop embedder is used and set as default."""
    annotation_collection_id = _create_annotation_collection(session=db_session)

    embed_dataset.embed_annotation_collection(
        session=db_session, annotation_collection_id=annotation_collection_id
    )

    # The registry embedder's space is registered as the collection's default.
    model_id = collection_embedding_model_resolver.get_default_by_collection_id(
        session=db_session, collection_id=annotation_collection_id
    )
    assert model_id is not None
    count = sample_embedding_resolver.get_embedding_count(
        session=db_session, collection_id=annotation_collection_id, embedding_model_id=model_id
    )
    assert count == 1


def test_embed_annotation_collection__no_registered_embedder_skips(
    db_session: Session,
    mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """With a default model but no embedder for its space, annotation embedding is skipped."""
    annotation_collection_id = _create_annotation_collection(session=db_session)
    _register_default_random_model(session=db_session, collection_id=annotation_collection_id)
    # An empty registry cannot supply an embedder for the default model's space.
    mocker.patch.object(embedder_registry, "get_registry", return_value=EmbedderRegistry())

    with caplog.at_level(level=logging.WARNING):
        embed_dataset.embed_annotation_collection(
            session=db_session, annotation_collection_id=annotation_collection_id
        )

    assert "No embedding model loaded" in caplog.text
    assert _stored_embeddings(session=db_session) == []


def test_embed_annotation_collection__stores_only_kept_crops(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    """Crops the embedder drops are left out, and kept vectors match their annotation IDs."""
    collection = create_collection(session=db_session)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    # One annotation per image at a distinct box x, on ordered paths so the resolver returns
    # the crops in a known order (it sorts by image path).
    box_xs = [100, 200, 300]
    annotation_sample_ids = []
    for index, box_x in enumerate(box_xs):
        image = create_image(
            session=db_session,
            collection_id=collection.collection_id,
            file_path_abs=f"/path/to/sample_{index}.png",
        )
        annotation = create_annotation(
            session=db_session,
            collection_id=collection.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=label.annotation_label_id,
            annotation_data={"x": box_x, "y": 0, "width": 20, "height": 20},
        )
        annotation_sample_ids.append(annotation.sample_id)
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    model_id = _register_default_random_model(
        session=db_session, collection_id=annotation_collection_id
    )
    registry = EmbedderRegistry()
    registry.register(embedder=_BoxXImageCropEmbedder())
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)

    embed_dataset.embed_annotation_collection(
        session=db_session, annotation_collection_id=annotation_collection_id
    )

    # The embedder drops the last crop by path order, so only the first two are stored, each
    # with the vector encoding its box's left edge.
    rows = sample_embedding_resolver.get_by_sample_ids(
        session=db_session, sample_ids=annotation_sample_ids, embedding_model_id=model_id
    )
    stored = {row.sample_id: list(row.embedding) for row in rows}
    assert stored == {
        annotation_sample_ids[0]: [box_xs[0]] * 3,
        annotation_sample_ids[1]: [box_xs[1]] * 3,
    }


def _register_default_random_model(session: Session, collection_id: UUID) -> UUID:
    """Register the random embedder's space as the collection's default and return its model ID."""
    model = create_embedding_model(
        session=session,
        collection_id=collection_id,
        embedding_model_name="random_model",
        embedding_dimension=3,
        set_as_default=True,
    )
    return model.embedding_model_id


def _create_annotation_collection(session: Session) -> UUID:
    """Create a collection with one annotated image and return its annotation child collection."""
    collection = create_collection(session=session)
    image = create_image(session=session, collection_id=collection.collection_id)
    label = create_annotation_label(session=session, root_collection_id=collection.collection_id)
    create_annotation(
        session=session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    return collection_resolver.get_or_create_child_collection(
        session=session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )


def _stored_embeddings(session: Session) -> list[SampleEmbeddingTable]:
    """Return every stored sample embedding, for asserting the skip path stores nothing."""
    return list(session.exec(select(SampleEmbeddingTable)).all())
