from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import numpy as np
import pytest
from lightly_studio_serve.embedder import ImageCropPathEmbedder
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec, ImageCrop
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.core.file_outcome_report import AllInputFilesFailedError
from lightly_studio.embed import embedder_registry
from lightly_studio.embed.embedder_registry import EmbedderRegistry
from lightly_studio.embed.random_embedder import RandomEmbedder
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import (
    annotation_label_resolver,
    annotation_resolver,
    collection_resolver,
)
from lightly_studio.services import annotations_service
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_embedding_model,
    create_image,
    create_sample_embedding,
)

EMBEDDING_DIMENSION = 3


class _CropOnlyEmbedder(ImageCropPathEmbedder):
    """Embeds crops with random vectors and has no text capability."""

    __slots__ = ()

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key="random_model", dimension=EMBEDDING_DIMENSION)

    def embed_image_crops(self, crops: list[ImageCrop]) -> EmbeddingResult:
        return EmbeddingResult(
            embeddings=np.random.rand(len(crops), EMBEDDING_DIMENSION).astype(np.float32),
            kept_indices=list(range(len(crops))),
        )


class _UnreadableImageEmbedder(ImageCropPathEmbedder):
    """Fails as a crop embedder does when no source image can be read."""

    __slots__ = ()

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key="random_model", dimension=EMBEDDING_DIMENSION)

    def embed_image_crops(self, crops: list[ImageCrop]) -> EmbeddingResult:
        del crops
        raise AllInputFilesFailedError("All 1 input files failed.")


@dataclass(frozen=True)
class _Setup:
    annotation: AnnotationBaseTable
    annotation_collection_id: UUID
    embedding_model_id: UUID
    root_collection_id: UUID
    dataset_id: UUID


def test_predict_annotation_classes__returns_every_dataset_label_sorted(
    db_session: Session, mocker: MockerFixture
) -> None:
    _patch_registry(mocker=mocker, embedder=RandomEmbedder(dimension=EMBEDDING_DIMENSION))
    setup = _create_setup(session=db_session, label_names=["bus", "cat", "dog"])

    predictions = annotations_service.predict_annotation_classes(
        session=db_session, annotation=setup.annotation
    )

    assert sorted(p.label_name for p in predictions) == ["bus", "cat", "dog"]
    scores = [p.score for p in predictions]
    assert scores == sorted(scores, reverse=True)
    assert sum(scores) == pytest.approx(1.0)


def test_predict_annotation_classes__stores_the_crop_embedding(
    db_session: Session, mocker: MockerFixture
) -> None:
    _patch_registry(mocker=mocker, embedder=RandomEmbedder(dimension=EMBEDDING_DIMENSION))
    setup = _create_setup(session=db_session, label_names=["cat"])

    annotations_service.predict_annotation_classes(session=db_session, annotation=setup.annotation)

    unembedded_ids = annotation_resolver.get_unembedded_annotation_ids(
        session=db_session,
        annotation_collection_id=setup.annotation_collection_id,
        embedding_model_id=setup.embedding_model_id,
    )
    assert setup.annotation.sample_id not in unembedded_ids


def test_predict_annotation_classes__no_crop_embedder_returns_empty(
    db_session: Session, mocker: MockerFixture
) -> None:
    mocker.patch.object(embedder_registry, "get_registry", return_value=EmbedderRegistry())
    setup = _create_setup(session=db_session, label_names=["cat", "dog"])

    predictions = annotations_service.predict_annotation_classes(
        session=db_session, annotation=setup.annotation
    )

    assert predictions == []


def test_predict_annotation_classes__no_text_embedder_and_no_neighbours_returns_zeros(
    db_session: Session, mocker: MockerFixture
) -> None:
    _patch_registry(mocker=mocker, embedder=_CropOnlyEmbedder())
    setup = _create_setup(session=db_session, label_names=["cat", "dog"])

    predictions = annotations_service.predict_annotation_classes(
        session=db_session, annotation=setup.annotation
    )

    assert [(p.label_name, p.score) for p in predictions] == [("cat", 0.0), ("dog", 0.0)]


def test_predict_annotation_classes__scores_by_labeled_neighbours(
    db_session: Session, mocker: MockerFixture
) -> None:
    # The crop-only embedder returns positive vectors, so the dog neighbour has a positive
    # similarity and no text anchor competes with it.
    _patch_registry(mocker=mocker, embedder=_CropOnlyEmbedder())
    setup = _create_setup(session=db_session, label_names=["cat", "dog"])
    dog = annotation_label_resolver.get_by_label_name(
        session=db_session, dataset_id=setup.dataset_id, label_name="dog"
    )
    assert dog is not None
    neighbour = create_annotation(
        session=db_session,
        collection_id=setup.root_collection_id,
        sample_id=setup.annotation.parent_sample_id,
        annotation_label_id=dog.annotation_label_id,
    )
    create_sample_embedding(
        session=db_session,
        sample_id=neighbour.sample_id,
        embedding_model_id=setup.embedding_model_id,
        embedding=[1.0, 1.0, 1.0],
    )

    predictions = annotations_service.predict_annotation_classes(
        session=db_session, annotation=setup.annotation
    )

    assert [(p.label_name, p.score) for p in predictions] == [
        ("dog", pytest.approx(1.0)),
        ("cat", 0.0),
    ]


def test_predict_annotation_classes__box_outside_image_returns_empty(
    db_session: Session, mocker: MockerFixture
) -> None:
    _patch_registry(mocker=mocker, embedder=RandomEmbedder(dimension=EMBEDDING_DIMENSION))
    setup = _create_setup(
        session=db_session,
        label_names=["cat", "dog"],
        image_size=(64, 64),
        box={"x": 10_000, "y": 0, "width": 10, "height": 10},
    )

    predictions = annotations_service.predict_annotation_classes(
        session=db_session, annotation=setup.annotation
    )

    assert predictions == []


def test_predict_annotation_classes__unreadable_image_returns_empty(
    db_session: Session, mocker: MockerFixture
) -> None:
    _patch_registry(mocker=mocker, embedder=_UnreadableImageEmbedder())
    setup = _create_setup(session=db_session, label_names=["cat", "dog"])

    predictions = annotations_service.predict_annotation_classes(
        session=db_session, annotation=setup.annotation
    )

    assert predictions == []


def _patch_registry(mocker: MockerFixture, embedder: ImageCropPathEmbedder) -> None:
    registry = EmbedderRegistry()
    registry.register(embedder=embedder)
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)


def _create_setup(
    session: Session,
    label_names: list[str],
    image_size: tuple[int, int] = (64, 64),
    box: dict[str, int] | None = None,
) -> _Setup:
    collection = create_collection(session=session)
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    labels = [
        create_annotation_label(
            session=session, root_collection_id=collection.collection_id, label_name=name
        )
        for name in label_names
    ]
    image = create_image(
        session=session,
        collection_id=collection.collection_id,
        width=image_size[0],
        height=image_size[1],
    )
    annotation = create_annotation(
        session=session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=labels[0].annotation_label_id,
        annotation_data=box or {"x": 8, "y": 8, "width": 16, "height": 16},
    )
    model = create_embedding_model(
        session=session,
        collection_id=annotation_collection_id,
        embedding_model_name="random_model",
        embedding_dimension=EMBEDDING_DIMENSION,
        set_as_default=True,
    )
    return _Setup(
        annotation=annotation,
        annotation_collection_id=annotation_collection_id,
        embedding_model_id=model.embedding_model_id,
        root_collection_id=collection.collection_id,
        dataset_id=collection.dataset_id,
    )
