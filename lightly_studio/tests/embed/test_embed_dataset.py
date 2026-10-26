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

from lightly_studio.core.file_outcome_report import AllInputFilesFailedError
from lightly_studio.embed import default_embedder, embed_dataset, embed_samples, embedder_registry
from lightly_studio.embed.embed_dataset import EmbedResult
from lightly_studio.embed.embedder_registry import EmbedderRegistry
from lightly_studio.embed.errors import NoUsableEmbedderError
from lightly_studio.embed.random_embedder import RandomEmbedder
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.resolvers import (
    annotation_resolver,
    collection_embedding_model_resolver,
    collection_resolver,
    image_resolver,
    sample_embedding_resolver,
)
from lightly_studio.resolvers.annotation_resolver.update_bounding_box import (
    BoundingBoxCoordinates,
)
from tests.helpers_resolvers import (
    ImageStub,
    create_annotation,
    create_annotation_label,
    create_collection,
    create_embedding_model,
    create_image,
    create_images,
    create_sample_embedding,
)

_RANDOM_EMBEDDING_DIMENSION = 3


class _FailOnCallEmbedder(ImagePathEmbedder):
    """Embeds paths as zeros and raises on a known call, as a failing embedder does.

    Shares the random model's space so it resolves as the collection's default.
    """

    __slots__ = ("_call_count", "_error", "_fail_on_call")

    def __init__(self, fail_on_call: int, error: Exception | None = None) -> None:
        self._call_count = 0
        self._error = error or RuntimeError("The embedder failed.")
        self._fail_on_call = fail_on_call

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        """Describe the shared random embedding space with dimension 3."""
        return EmbeddingSpaceSpec(space_key="random_model", dimension=3)

    def embed_images(self, paths: list[str]) -> EmbeddingResult:
        """Embed every path as zeros, or raise on call number ``fail_on_call``."""
        self._call_count += 1
        if self._call_count == self._fail_on_call:
            raise self._error
        return EmbeddingResult(
            embeddings=np.zeros((len(paths), 3), dtype=np.float32),
            kept_indices=list(range(len(paths))),
        )


class _FailOnPathsEmbedder(ImagePathEmbedder):
    """Embeds paths as zeros, but raises when every path of a call is in ``failing_paths``.

    Shares the random model's space so it resolves as the collection's default.
    """

    __slots__ = ("_failing_paths",)

    def __init__(self, failing_paths: set[str]) -> None:
        self._failing_paths = failing_paths

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        """Describe the shared random embedding space with dimension 3."""
        return EmbeddingSpaceSpec(space_key="random_model", dimension=3)

    def embed_images(self, paths: list[str]) -> EmbeddingResult:
        """Embed every path as zeros, or raise if all paths are failing."""
        if all(path in self._failing_paths for path in paths):
            raise AllInputFilesFailedError("All input files failed.")
        return EmbeddingResult(
            embeddings=np.zeros((len(paths), 3), dtype=np.float32),
            kept_indices=list(range(len(paths))),
        )


class _BoxXImageCropEmbedder(ImageCropPathEmbedder):
    """Embeds each crop as its left edge x, optionally dropping the last crop.

    Deriving the vector from the crop's box, not the input position, makes the test fail
    if ``embed_annotation_crops`` matches crops to the wrong annotation IDs. Shares the
    random model's space so it resolves as the collection's default.
    """

    __slots__ = ("_drop_last",)

    def __init__(self, drop_last: bool = False) -> None:
        self._drop_last = drop_last

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        """Describe the shared random embedding space with dimension 3."""
        return EmbeddingSpaceSpec(space_key="random_model", dimension=3)

    def embed_image_crops(self, crops: list[ImageCrop]) -> EmbeddingResult:
        """Embed the crops as [x, x, x], read from the crop's left edge."""
        kept_indices = list(range(len(crops) - 1 if self._drop_last else len(crops)))
        embeddings = np.array([[crops[index].x] * 3 for index in kept_indices], dtype=np.float32)
        return EmbeddingResult(embeddings=embeddings, kept_indices=kept_indices)


class _EditBoxDuringEmbedCropEmbedder(ImageCropPathEmbedder):
    """Embeds crops as [x, x, x], after moving the box of an annotation in the database.

    Simulates a user editing a box while the embedder runs.
    """

    __slots__ = ("_annotation_id", "_new_x", "_session")

    def __init__(self, session: Session, annotation_id: UUID, new_x: int) -> None:
        self._session = session
        self._annotation_id = annotation_id
        self._new_x = new_x

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        """Describe the shared random embedding space with dimension 3."""
        return EmbeddingSpaceSpec(space_key="random_model", dimension=3)

    def embed_image_crops(self, crops: list[ImageCrop]) -> EmbeddingResult:
        """Edit the box, then embed the crops that were read before the edit."""
        annotation_resolver.update_bounding_box(
            session=self._session,
            annotation_id=self._annotation_id,
            coordinates=BoundingBoxCoordinates(x=self._new_x, y=0, width=20, height=20),
        )
        embeddings = np.array([[crop.x] * 3 for crop in crops], dtype=np.float32)
        return EmbeddingResult(embeddings=embeddings, kept_indices=list(range(len(crops))))


class _FailingImageCropEmbedder(ImageCropPathEmbedder):
    """Raises for every call. Shares the random model's space."""

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        """Describe the shared random embedding space with dimension 3."""
        return EmbeddingSpaceSpec(space_key="random_model", dimension=3)

    def embed_image_crops(self, crops: list[ImageCrop]) -> EmbeddingResult:
        """Fail as if every crop file were unreadable."""
        del crops
        raise AllInputFilesFailedError("All input files failed.")


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

    assert stored == EmbedResult(stored=2, failed_chunks=0)
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
    assert embed_dataset.embed_missing_images(
        session=db_session, collection_id=collection.collection_id
    ) == EmbedResult(stored=2, failed_chunks=0)
    create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="/test/c.jpg")],
    )

    stored = embed_dataset.embed_missing_images(
        session=db_session, collection_id=collection.collection_id
    )

    assert stored == EmbedResult(stored=1, failed_chunks=0)
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

    assert stored == EmbedResult(stored=3, failed_chunks=0)
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

    assert stored == EmbedResult(stored=0, failed_chunks=0)
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
    assert embed_dataset.embed_missing_images(
        session=db_session, collection_id=collection.collection_id
    ) == EmbedResult(stored=2, failed_chunks=0)
    spy = mocker.spy(default_embedder, "resolve_default_embedder")

    stored = embed_dataset.embed_missing_images(
        session=db_session, collection_id=collection.collection_id
    )

    assert stored == EmbedResult(stored=0, failed_chunks=0)
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

    assert stored == EmbedResult(stored=5, failed_chunks=0)
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


def test_embed_missing_images__skip_failed_chunks_continues(
    db_session: Session, mocker: MockerFixture
) -> None:
    """With skip_failed_chunks, a chunk where every file failed is skipped."""
    collection = create_collection(session=db_session)
    create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path=f"/test/{index}.jpg") for index in range(2)],
    )
    _register_default_random_model(session=db_session, collection_id=collection.collection_id)
    mocker.patch.object(embed_dataset, "_IMAGE_EMBED_BATCH_SIZE", 1)
    registry = EmbedderRegistry()
    registry.register(
        embedder=_FailOnCallEmbedder(fail_on_call=1, error=AllInputFilesFailedError("failed"))
    )
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)

    stored = embed_dataset.embed_missing_images(
        session=db_session, collection_id=collection.collection_id, skip_failed_chunks=True
    )

    assert stored == EmbedResult(stored=1, failed_chunks=1)


def test_embed_missing_images__failed_chunk_raises_by_default(
    db_session: Session, mocker: MockerFixture
) -> None:
    """Without skip_failed_chunks, AllInputFilesFailedError propagates."""
    collection = create_collection(session=db_session)
    create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="/test/0.jpg")],
    )
    _register_default_random_model(session=db_session, collection_id=collection.collection_id)
    registry = EmbedderRegistry()
    registry.register(
        embedder=_FailOnCallEmbedder(fail_on_call=1, error=AllInputFilesFailedError("failed"))
    )
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)

    with pytest.raises(AllInputFilesFailedError):
        embed_dataset.embed_missing_images(
            session=db_session, collection_id=collection.collection_id
        )


@pytest.mark.usefixtures("patched_registry")
def test_embed_annotation_crops(db_session: Session) -> None:
    """Annotation crops are stored under the collection's default model, via the registry."""
    annotation_collection_id, _ = _create_annotation_collection(session=db_session, box_xs=[10])
    model_id = _register_default_random_model(
        session=db_session, collection_id=annotation_collection_id
    )

    stored = embed_dataset.embed_annotation_crops(
        session=db_session, annotation_collection_id=annotation_collection_id
    )

    assert stored == EmbedResult(stored=1, failed_chunks=0)
    count = sample_embedding_resolver.get_embedding_count(
        session=db_session, collection_id=annotation_collection_id, embedding_model_id=model_id
    )
    assert count == 1


@pytest.mark.usefixtures("patched_registry")
def test_embed_annotation_crops__no_default_registers_registry_default(
    db_session: Session,
) -> None:
    """With no default model, the registry's crop embedder is used and set as default."""
    annotation_collection_id, _ = _create_annotation_collection(session=db_session, box_xs=[10])

    embed_dataset.embed_annotation_crops(
        session=db_session, annotation_collection_id=annotation_collection_id
    )

    model_id = collection_embedding_model_resolver.get_default_by_collection_id(
        session=db_session, collection_id=annotation_collection_id
    )
    assert model_id is not None
    count = sample_embedding_resolver.get_embedding_count(
        session=db_session, collection_id=annotation_collection_id, embedding_model_id=model_id
    )
    assert count == 1


def test_embed_annotation_crops__no_registered_embedder_returns_none(
    db_session: Session,
    mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """With a default model but no embedder for its space, annotation embedding is skipped."""
    annotation_collection_id, _ = _create_annotation_collection(session=db_session, box_xs=[10])
    _register_default_random_model(session=db_session, collection_id=annotation_collection_id)
    # An empty registry cannot supply an embedder for the default model's space.
    mocker.patch.object(embedder_registry, "get_registry", return_value=EmbedderRegistry())

    with caplog.at_level(level=logging.WARNING):
        stored = embed_dataset.embed_annotation_crops(
            session=db_session, annotation_collection_id=annotation_collection_id
        )

    assert stored is None
    assert "No embedding model loaded" in caplog.text
    assert _stored_embeddings(session=db_session) == []


def test_embed_annotation_crops__classification_only_registers_no_default(
    db_session: Session, mocker: MockerFixture
) -> None:
    """Without a croppable annotation, the embedder is not resolved and no model registers."""
    annotation_collection_id, _ = _create_annotation_collection(
        session=db_session, box_xs=[10], annotation_type=AnnotationType.CLASSIFICATION
    )
    spy = mocker.spy(default_embedder, "resolve_default_embedder")

    stored = embed_dataset.embed_annotation_crops(
        session=db_session, annotation_collection_id=annotation_collection_id
    )

    assert stored == EmbedResult(stored=0, failed_chunks=0)
    spy.assert_not_called()
    assert (
        collection_embedding_model_resolver.get_default_by_collection_id(
            session=db_session, collection_id=annotation_collection_id
        )
        is None
    )


def test_embed_annotation_crops__stores_only_kept_crops(
    db_session: Session, mocker: MockerFixture
) -> None:
    """Crops the embedder drops are left out, and kept vectors match their annotation IDs."""
    box_xs = [100, 200, 300]
    annotation_collection_id, annotation_ids = _create_annotation_collection(
        session=db_session, box_xs=box_xs
    )
    model_id = _register_default_random_model(
        session=db_session, collection_id=annotation_collection_id
    )
    _patch_registry(mocker=mocker, embedder=_BoxXImageCropEmbedder(drop_last=True))

    embed_dataset.embed_annotation_crops(
        session=db_session, annotation_collection_id=annotation_collection_id
    )

    stored = _stored_by_annotation(
        session=db_session, annotation_ids=annotation_ids, model_id=model_id
    )
    assert stored == {annotation_ids[0]: [100.0] * 3, annotation_ids[1]: [200.0] * 3}


def test_embed_annotation_crops__recompute_overwrites_existing(
    db_session: Session, mocker: MockerFixture
) -> None:
    """With recompute, a stored crop embedding is replaced."""
    annotation_collection_id, annotation_ids = _create_annotation_collection(
        session=db_session, box_xs=[100]
    )
    model_id = _register_default_random_model(
        session=db_session, collection_id=annotation_collection_id
    )
    _store_zero_embeddings(session=db_session, annotation_ids=annotation_ids, model_id=model_id)
    _patch_registry(mocker=mocker, embedder=_BoxXImageCropEmbedder())

    embed_dataset.embed_annotation_crops(
        session=db_session, annotation_collection_id=annotation_collection_id, recompute=True
    )

    stored = _stored_by_annotation(
        session=db_session, annotation_ids=annotation_ids, model_id=model_id
    )
    assert stored == {annotation_ids[0]: [100.0] * 3}


def test_embed_annotation_crops__default_keeps_existing(
    db_session: Session, mocker: MockerFixture
) -> None:
    """Without recompute, a stored crop embedding is left alone."""
    annotation_collection_id, annotation_ids = _create_annotation_collection(
        session=db_session, box_xs=[100]
    )
    model_id = _register_default_random_model(
        session=db_session, collection_id=annotation_collection_id
    )
    _store_zero_embeddings(session=db_session, annotation_ids=annotation_ids, model_id=model_id)
    _patch_registry(mocker=mocker, embedder=_BoxXImageCropEmbedder())

    stored_count = embed_dataset.embed_annotation_crops(
        session=db_session, annotation_collection_id=annotation_collection_id
    )

    assert stored_count == EmbedResult(stored=0, failed_chunks=0)
    stored = _stored_by_annotation(
        session=db_session, annotation_ids=annotation_ids, model_id=model_id
    )
    assert stored == {annotation_ids[0]: [0.0] * 3}


def test_embed_annotation_crops__dropped_crop_keeps_old_vector(
    db_session: Session, mocker: MockerFixture
) -> None:
    """With recompute, a crop the embedder drops keeps its earlier vector."""
    annotation_collection_id, annotation_ids = _create_annotation_collection(
        session=db_session, box_xs=[100, 200]
    )
    model_id = _register_default_random_model(
        session=db_session, collection_id=annotation_collection_id
    )
    _store_zero_embeddings(session=db_session, annotation_ids=annotation_ids, model_id=model_id)
    _patch_registry(mocker=mocker, embedder=_BoxXImageCropEmbedder(drop_last=True))

    embed_dataset.embed_annotation_crops(
        session=db_session, annotation_collection_id=annotation_collection_id, recompute=True
    )

    stored = _stored_by_annotation(
        session=db_session, annotation_ids=annotation_ids, model_id=model_id
    )
    assert stored == {annotation_ids[0]: [100.0] * 3, annotation_ids[1]: [0.0] * 3}


def test_embed_annotation_crops__stores_fingerprint(
    db_session: Session, mocker: MockerFixture
) -> None:
    """The stored row carries the fingerprint of the box the crop was read from."""
    annotation_collection_id, annotation_ids = _create_annotation_collection(
        session=db_session, box_xs=[100]
    )
    model_id = _register_default_random_model(
        session=db_session, collection_id=annotation_collection_id
    )
    _patch_registry(mocker=mocker, embedder=_BoxXImageCropEmbedder())

    embed_dataset.embed_annotation_crops(
        session=db_session, annotation_collection_id=annotation_collection_id
    )

    row = db_session.get(SampleEmbeddingTable, (annotation_ids[0], model_id))
    assert row is not None
    [crop] = annotation_resolver.get_annotation_crops_for_ids(
        session=db_session, annotation_sample_ids=annotation_ids
    )
    assert row.source_fingerprint == crop.source_fingerprint


def test_embed_annotation_crops__box_edited_during_run(
    db_session: Session, mocker: MockerFixture
) -> None:
    """A box edited while embedding leaves the old vector with the old fingerprint."""
    annotation_collection_id, annotation_ids = _create_annotation_collection(
        session=db_session, box_xs=[10]
    )
    model_id = _register_default_random_model(
        session=db_session, collection_id=annotation_collection_id
    )
    _patch_registry(
        mocker=mocker,
        embedder=_EditBoxDuringEmbedCropEmbedder(
            session=db_session, annotation_id=annotation_ids[0], new_x=30
        ),
    )

    embed_dataset.embed_annotation_crops(
        session=db_session, annotation_collection_id=annotation_collection_id
    )

    stored = _stored_by_annotation(
        session=db_session, annotation_ids=annotation_ids, model_id=model_id
    )
    assert stored == {annotation_ids[0]: [10.0] * 3}
    row = db_session.get(SampleEmbeddingTable, (annotation_ids[0], model_id))
    assert row is not None
    [current] = annotation_resolver.get_annotation_crops_for_ids(
        session=db_session, annotation_sample_ids=annotation_ids
    )
    assert row.source_fingerprint != current.source_fingerprint


@pytest.mark.usefixtures("patched_registry")
def test_embed_annotation_crops__box_outside_image_is_skipped(
    db_session: Session, caplog: pytest.LogCaptureFixture
) -> None:
    """A box fully outside its image is skipped, and a rerun still finishes."""
    # The image is 1920x1080, so the second box lies fully outside it.
    annotation_collection_id, _ = _create_annotation_collection(
        session=db_session, box_xs=[100, 5000]
    )

    with caplog.at_level(level=logging.WARNING):
        first = embed_dataset.embed_annotation_crops(
            session=db_session, annotation_collection_id=annotation_collection_id
        )
    second = embed_dataset.embed_annotation_crops(
        session=db_session, annotation_collection_id=annotation_collection_id
    )

    assert first == EmbedResult(stored=1, failed_chunks=0)
    assert "Skipping invalid annotation crop" in caplog.text
    assert second == EmbedResult(stored=0, failed_chunks=0)


def test_compute_embeddings__every_chunk_fails_raises(
    db_session: Session, mocker: MockerFixture
) -> None:
    """When at least one chunk failed and nothing was stored, the error propagates."""
    collection = create_collection(session=db_session)
    create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="/test/a.jpg"), ImageStub(path="/test/b.jpg")],
    )
    mocker.patch.object(embed_dataset, "_IMAGE_EMBED_BATCH_SIZE", 1)
    _patch_image_registry(
        mocker=mocker, embedder=_FailOnPathsEmbedder(failing_paths={"/test/a.jpg", "/test/b.jpg"})
    )

    with pytest.raises(AllInputFilesFailedError):
        embed_dataset.compute_embeddings(
            session=db_session,
            collection_id=collection.collection_id,
            embed_annotations=False,
            recompute_annotations=False,
        )


def test_compute_embeddings__every_crop_chunk_fails_raises(
    db_session: Session, mocker: MockerFixture
) -> None:
    """With the images already embedded, a crop embed where every chunk fails raises."""
    annotation_collection_id, _ = _create_annotation_collection(session=db_session, box_xs=[100])
    annotation_collection = db_session.get(CollectionTable, annotation_collection_id)
    assert annotation_collection is not None
    image_collection_id = annotation_collection.parent_collection_id
    assert image_collection_id is not None
    image_model_id = _register_default_random_model(
        session=db_session, collection_id=image_collection_id
    )
    for image_sample_id in db_session.exec(select(ImageTable.sample_id)).all():
        create_sample_embedding(
            session=db_session,
            sample_id=image_sample_id,
            embedding_model_id=image_model_id,
            embedding=[0.0, 0.0, 0.0],
        )
    _register_default_random_model(session=db_session, collection_id=annotation_collection_id)
    _patch_registry(mocker=mocker, embedder=_FailingImageCropEmbedder())

    with pytest.raises(AllInputFilesFailedError):
        embed_dataset.compute_embeddings(
            session=db_session,
            collection_id=image_collection_id,
            embed_annotations=True,
            recompute_annotations=False,
        )


def test_compute_embeddings__some_chunks_fail(db_session: Session, mocker: MockerFixture) -> None:
    """A failed chunk is skipped while the other chunks are stored."""
    collection = create_collection(session=db_session)
    images = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="/test/a.jpg"), ImageStub(path="/test/b.jpg")],
    )
    mocker.patch.object(embed_dataset, "_IMAGE_EMBED_BATCH_SIZE", 1)
    _patch_image_registry(
        mocker=mocker, embedder=_FailOnPathsEmbedder(failing_paths={"/test/a.jpg"})
    )

    embed_dataset.compute_embeddings(
        session=db_session,
        collection_id=collection.collection_id,
        embed_annotations=True,
        recompute_annotations=False,
    )

    stored_ids = [embedding.sample_id for embedding in _stored_embeddings(session=db_session)]
    assert stored_ids == [images[1].sample_id]


def test_compute_embeddings__no_usable_embedder_raises(
    db_session: Session, mocker: MockerFixture
) -> None:
    """Images that need an embedding and no embedder raise NoUsableEmbedderError."""
    collection = create_collection(session=db_session)
    create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="/test/a.jpg")],
    )
    mocker.patch.object(embedder_registry, "get_registry", return_value=EmbedderRegistry())
    # No built-in model loads in this test
    mocker.patch.object(embedder_registry, "_load_builtin_embedder", return_value=None)

    with pytest.raises(NoUsableEmbedderError):
        embed_dataset.compute_embeddings(
            session=db_session,
            collection_id=collection.collection_id,
            embed_annotations=True,
            recompute_annotations=False,
        )


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


def _stored_embeddings(session: Session) -> list[SampleEmbeddingTable]:
    """Return every stored sample embedding, for asserting the skip path stores nothing."""
    return list(session.exec(select(SampleEmbeddingTable)).all())


def _patch_image_registry(mocker: MockerFixture, embedder: ImagePathEmbedder) -> None:
    """Route embedding to a fresh registry holding only the given image embedder."""
    registry = EmbedderRegistry()
    registry.register(embedder=embedder)
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)


def _patch_registry(mocker: MockerFixture, embedder: ImageCropPathEmbedder) -> None:
    """Route embedding to a fresh registry holding only the given crop embedder."""
    registry = EmbedderRegistry()
    registry.register(embedder=embedder)
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)


def _create_annotation_collection(
    session: Session,
    box_xs: list[int],
    annotation_type: AnnotationType = AnnotationType.OBJECT_DETECTION,
) -> tuple[UUID, list[UUID]]:
    """Create one annotated image per box x and return the annotation collection and IDs.

    The image paths are ordered like ``box_xs``, which is the order crops are embedded in.
    """
    collection = create_collection(session=session)
    label = create_annotation_label(session=session, root_collection_id=collection.collection_id)
    annotation_ids = []
    for index, box_x in enumerate(box_xs):
        image = create_image(
            session=session,
            collection_id=collection.collection_id,
            file_path_abs=f"/path/to/sample_{index}.png",
        )
        annotation = create_annotation(
            session=session,
            collection_id=collection.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=label.annotation_label_id,
            annotation_data={"x": box_x, "y": 0, "width": 20, "height": 20},
            annotation_type=annotation_type,
        )
        annotation_ids.append(annotation.sample_id)
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    return annotation_collection_id, annotation_ids


def _store_zero_embeddings(session: Session, annotation_ids: list[UUID], model_id: UUID) -> None:
    """Store the vector [0, 0, 0] for each annotation."""
    for annotation_id in annotation_ids:
        create_sample_embedding(
            session=session,
            sample_id=annotation_id,
            embedding_model_id=model_id,
            embedding=[0.0, 0.0, 0.0],
        )


def _stored_by_annotation(
    session: Session, annotation_ids: list[UUID], model_id: UUID
) -> dict[UUID, list[float]]:
    """Return the stored vector of each annotation that has one."""
    rows = sample_embedding_resolver.get_by_sample_ids(
        session=session, sample_ids=annotation_ids, embedding_model_id=model_id
    )
    return {row.sample_id: [float(value) for value in row.embedding] for row in rows}
