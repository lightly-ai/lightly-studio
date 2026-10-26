from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID, uuid4

import numpy as np
import pytest
from lightly_studio_serve.embedder import ImagePathEmbedder
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec
from PIL import Image
from pytest_mock import MockerFixture as Mocker
from sqlmodel import col, select

from lightly_studio import ImageDataset
from lightly_studio.core.file_outcome_report import AllInputFilesFailedError
from lightly_studio.embed import (
    default_embedder,
    embed_dataset,
    embedder_registry,
    embedding_storage,
)
from lightly_studio.embed.embedder_registry import EmbedderRegistry
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.resolvers import (
    annotation_resolver,
    collection_embedding_model_resolver,
    collection_resolver,
)
from tests.helpers_resolvers import create_annotation, create_annotation_label

_EMBEDDING_DIMENSION = 3
_SKIP_WARNING = "Skipping a chunk of 1 images where every file failed."


class _MissingFileImageEmbedder(ImagePathEmbedder):
    """Raises ``AllInputFilesFailedError`` when no path exists, else embeds zeros.

    Shares the random model's space so it resolves as the collection's default.
    """

    __slots__ = ()

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        """Describe the shared random embedding space with dimension 3."""
        return EmbeddingSpaceSpec(space_key="random_model", dimension=_EMBEDDING_DIMENSION)

    def embed_images(self, paths: list[str]) -> EmbeddingResult:
        """Embed existing paths as zeros."""
        if not any(Path(path).exists() for path in paths):
            raise AllInputFilesFailedError("All input files failed.")
        return EmbeddingResult(
            embeddings=np.zeros((len(paths), _EMBEDDING_DIMENSION), dtype=np.float32),
            kept_indices=list(range(len(paths))),
        )


def test_compute_embeddings__dataset_added_without_embedding(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    dataset = _create_dataset(tmp_path=tmp_path, image_names=["a.jpg", "b.jpg"])
    sample_ids = _image_sample_ids(dataset=dataset)
    for sample_id in sample_ids:
        _create_box(dataset=dataset, sample_id=sample_id, source="ground_truth")

    dataset.compute_embeddings()

    annotation_sample_ids = _annotation_sample_ids(dataset=dataset)
    assert len(annotation_sample_ids) == 2
    for sample_id in [*sample_ids, *annotation_sample_ids]:
        assert len(_vectors(dataset=dataset, sample_ids=[sample_id])) == 1


def test_compute_embeddings__every_annotation_source(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    dataset = _create_dataset(tmp_path=tmp_path, image_names=["a.jpg"])
    sample_id = _image_sample_ids(dataset=dataset)[0]
    _create_box(dataset=dataset, sample_id=sample_id, source="ground_truth")
    _create_box(dataset=dataset, sample_id=sample_id, source="predictions")

    dataset.compute_embeddings()

    source_names = {
        c.name
        for c in collection_resolver.get_annotation_collections(
            session=dataset.session, parent_collection_id=dataset.collection_id
        )
    }
    assert source_names == {"ground_truth", "predictions"}
    assert len(_vectors(dataset=dataset, sample_ids=_annotation_sample_ids(dataset=dataset))) == 2


def test_compute_embeddings__embed_annotations_false(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    dataset = _create_dataset(tmp_path=tmp_path, image_names=["a.jpg"])
    sample_id = _image_sample_ids(dataset=dataset)[0]
    _create_box(dataset=dataset, sample_id=sample_id, source="ground_truth")

    dataset.compute_embeddings(embed_annotations=False)

    assert len(_vectors(dataset=dataset, sample_ids=[sample_id])) == 1
    assert _vectors(dataset=dataset, sample_ids=_annotation_sample_ids(dataset=dataset)) == {}


def test_compute_embeddings__recompute_annotations(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    dataset = _create_dataset(tmp_path=tmp_path, image_names=["a.jpg"])
    sample_id = _image_sample_ids(dataset=dataset)[0]
    _create_box(dataset=dataset, sample_id=sample_id, source="ground_truth")
    dataset.compute_embeddings()
    annotation_sample_id = _annotation_sample_ids(dataset=dataset)[0]
    annotation_collection = collection_resolver.get_annotation_collections(
        session=dataset.session, parent_collection_id=dataset.collection_id
    )[0]
    model_id = collection_embedding_model_resolver.get_default_by_collection_id(
        session=dataset.session, collection_id=annotation_collection.collection_id
    )
    assert model_id is not None
    known_vector = (1.0, 2.0, 3.0)
    embedding_storage.store_embeddings(
        session=dataset.session,
        model_id=model_id,
        sample_ids=[annotation_sample_id],
        embeddings=np.array([known_vector], dtype=np.float32),
        show_progress=False,
        replace=True,
    )

    dataset.compute_embeddings()
    assert _vectors(dataset=dataset, sample_ids=[annotation_sample_id]) == {
        annotation_sample_id: known_vector
    }

    dataset.compute_embeddings(recompute_annotations=True)
    assert (
        _vectors(dataset=dataset, sample_ids=[annotation_sample_id])[annotation_sample_id]
        != known_vector
    )


def test_compute_embeddings__second_run_is_noop(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
    mocker: Mocker,
) -> None:
    dataset = _create_dataset(tmp_path=tmp_path, image_names=["a.jpg"])
    sample_id = _image_sample_ids(dataset=dataset)[0]
    _create_box(dataset=dataset, sample_id=sample_id, source="ground_truth")
    dataset.compute_embeddings()
    all_ids = [sample_id, *_annotation_sample_ids(dataset=dataset)]
    before = _vectors(dataset=dataset, sample_ids=all_ids)
    spy = mocker.spy(default_embedder, "resolve_default_embedder")

    dataset.compute_embeddings()

    assert _vectors(dataset=dataset, sample_ids=all_ids) == before
    spy.assert_not_called()


def test_compute_embeddings__nothing_to_embed_and_no_embedder__empty_dataset(
    patch_collection: None,  # noqa: ARG001
    mocker: Mocker,
) -> None:
    dataset = ImageDataset.create(name="test_dataset")
    _patch_empty_registry(mocker=mocker)

    dataset.compute_embeddings()

    assert (
        collection_embedding_model_resolver.get_default_by_collection_id(
            session=dataset.session, collection_id=dataset.collection_id
        )
        is None
    )


def test_compute_embeddings__nothing_to_embed_and_no_embedder__classification_only(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
    mocker: Mocker,
) -> None:
    dataset = _create_dataset(tmp_path=tmp_path, image_names=["a.jpg"])
    sample_id = _image_sample_ids(dataset=dataset)[0]
    dataset.compute_embeddings()
    label = create_annotation_label(
        session=dataset.session, root_collection_id=dataset.collection_id
    )
    create_annotation(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_id=sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
        annotation_data={},
        annotation_collection_name="ground_truth",
    )
    _patch_empty_registry(mocker=mocker)

    dataset.compute_embeddings()

    annotation_collection = collection_resolver.get_annotation_collections(
        session=dataset.session, parent_collection_id=dataset.collection_id
    )[0]
    assert (
        collection_embedding_model_resolver.get_default_by_collection_id(
            session=dataset.session, collection_id=annotation_collection.collection_id
        )
        is None
    )


def test_compute_embeddings__failed_chunk_is_logged_and_next_embedded(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
    mocker: Mocker,
    caplog: pytest.LogCaptureFixture,
) -> None:
    dataset = _create_dataset(tmp_path=tmp_path, image_names=["a.jpg", "b.jpg"])
    mocker.patch.object(embed_dataset, "_IMAGE_EMBED_BATCH_SIZE", 1)
    (tmp_path / "a.jpg").unlink()
    _patch_registry(mocker=mocker)

    with caplog.at_level(logging.WARNING):
        dataset.compute_embeddings()

    assert _embedded_file_names(dataset=dataset) == {"b.jpg"}
    assert caplog.text.count(_SKIP_WARNING) == 1


def _create_dataset(tmp_path: Path, image_names: list[str]) -> ImageDataset:
    for name in image_names:
        Image.new("RGB", (100, 100)).save(tmp_path / name)
    dataset = ImageDataset.create(name="test_dataset")
    dataset.add_images_from_path(path=tmp_path, embed=False)
    return dataset


def _patch_empty_registry(mocker: Mocker) -> None:
    mocker.patch.object(embedder_registry, "get_registry", return_value=EmbedderRegistry())
    # No built-in model loads in these tests
    mocker.patch.object(embedder_registry, "_load_builtin_embedder", return_value=None)


def _patch_registry(mocker: Mocker) -> None:
    registry = EmbedderRegistry()
    registry.register(embedder=_MissingFileImageEmbedder())
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)


def _image_sample_ids(dataset: ImageDataset) -> list[UUID]:
    return [sample.sample_id for sample in dataset.query().to_list()]


def _create_box(dataset: ImageDataset, sample_id: UUID, source: str) -> None:
    label = create_annotation_label(
        session=dataset.session, root_collection_id=dataset.collection_id, label_name=uuid4().hex
    )
    create_annotation(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_id=sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_collection_name=source,
    )


def _annotation_sample_ids(dataset: ImageDataset) -> list[UUID]:
    ids: list[UUID] = []
    for annotation_collection in collection_resolver.get_annotation_collections(
        session=dataset.session, parent_collection_id=dataset.collection_id
    ):
        ids.extend(
            annotation_resolver.get_croppable_annotation_ids(
                session=dataset.session,
                annotation_collection_id=annotation_collection.collection_id,
            )
        )
    return ids


def _vectors(dataset: ImageDataset, sample_ids: list[UUID]) -> dict[UUID, tuple[float, ...]]:
    dataset.session.expire_all()
    rows = dataset.session.exec(
        select(SampleEmbeddingTable).where(col(SampleEmbeddingTable.sample_id).in_(sample_ids))
    ).all()
    return {row.sample_id: tuple(float(v) for v in row.embedding) for row in rows}


def _embedded_file_names(dataset: ImageDataset) -> set[str]:
    dataset.session.expire_all()
    return {
        sample.file_name
        for sample in dataset.query().to_list()
        if len(sample.sample_table.embeddings) > 0
    }
