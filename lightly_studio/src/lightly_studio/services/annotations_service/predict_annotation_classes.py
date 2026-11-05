"""Predict the class of an annotation from its crop."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

import numpy as np
from lightly_studio_serve.embedder import ImageCropPathEmbedder, TextEmbedder
from numpy.typing import NDArray
from sqlmodel import Session

from lightly_studio.core.file_outcome_report import AllInputFilesFailedError
from lightly_studio.embed import default_embedder, embed_samples
from lightly_studio.embed.errors import MissingCapabilityError
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.resolvers import (
    annotation_label_resolver,
    annotation_resolver,
    collection_resolver,
    sample_embedding_resolver,
)
from lightly_studio.services.annotations_service import class_prediction_scoring

KNN_NEIGHBOUR_COUNT = 10
TEXT_ANCHOR_PROMPT = "a photo of a {class_name}"

# Text anchor embeddings, L2-normalized, keyed by embedding model ID and class name.
_text_anchor_cache: dict[tuple[UUID, str], NDArray[np.float32]] = {}


@dataclass(frozen=True)
class AnnotationClassPrediction:
    """Predicted score of one class for an annotation.

    Attributes:
        annotation_label_id: The class.
        label_name: Name of the class.
        score: Share of the evidence for this class. The scores of one prediction sum to 1,
            or are all 0 when there is no evidence.
    """

    annotation_label_id: UUID
    label_name: str
    score: float


def predict_annotation_classes(
    session: Session,
    annotation: AnnotationBaseTable,
) -> list[AnnotationClassPrediction]:
    """Predict the class of an annotation from the crop of its bounding box.

    Embeds and stores the crop, then scores every class of the dataset by the crop's nearest
    labeled annotations and by one text anchor per class.

    Args:
        session: Database session for resolver operations.
        annotation: An object-detection or segmentation-mask annotation.

    Returns:
        Every class of the dataset, highest score first. Empty when the crop cannot be embedded,
        for example because no crop embedder is available or the box is outside the image.
    """
    annotation_collection_id = annotation.sample.collection_id
    resolved = default_embedder.resolve_default_embedder(
        session=session,
        collection_id=annotation_collection_id,
        embedder_type=ImageCropPathEmbedder,
    )
    if resolved is None:
        return []
    crop_embedder, embedding_model_id = resolved

    crop_embedding = _embed_crop(
        session=session,
        embedder=crop_embedder,
        embedding_model_id=embedding_model_id,
        annotation_id=annotation.sample_id,
    )
    if crop_embedding is None:
        return []

    neighbours = annotation_resolver.get_nearest_labeled_annotations(
        session=session,
        annotation_collection_id=annotation_collection_id,
        embedding_model_id=embedding_model_id,
        query_embedding=crop_embedding.tolist(),
        exclude_annotation_id=annotation.sample_id,
        limit=KNN_NEIGHBOUR_COUNT,
    )
    collection = collection_resolver.get_by_id(
        session=session, collection_id=annotation_collection_id
    )
    assert collection is not None
    labels = annotation_label_resolver.get_all(session=session, dataset_id=collection.dataset_id)
    text_similarities = _get_text_similarities(
        session=session,
        annotation_collection_id=annotation_collection_id,
        embedding_model_id=embedding_model_id,
        labels=labels,
        crop_embedding=crop_embedding,
    )

    scores = class_prediction_scoring.score_classes(
        label_ids=[label.annotation_label_id for label in labels],
        neighbours=neighbours,
        text_similarities=text_similarities,
    )
    predictions = [
        AnnotationClassPrediction(
            annotation_label_id=label.annotation_label_id,
            label_name=label.annotation_label_name,
            score=scores[label.annotation_label_id],
        )
        for label in labels
    ]
    return sorted(predictions, key=lambda p: (-p.score, p.label_name))


def _embed_crop(
    session: Session,
    embedder: ImageCropPathEmbedder,
    embedding_model_id: UUID,
    annotation_id: UUID,
) -> NDArray[np.float32] | None:
    """Embed and store the crop of an annotation, and return its embedding.

    Returns:
        The stored embedding, or None when the crop could not be embedded, for example
        because the source image is missing or broken.
    """
    try:
        embed_samples.embed_annotation_crops(
            session=session,
            embedder=embedder,
            model_id=embedding_model_id,
            annotation_sample_ids=[annotation_id],
        )
    except AllInputFilesFailedError:
        return None
    rows = sample_embedding_resolver.get_by_sample_ids(
        session=session, sample_ids=[annotation_id], embedding_model_id=embedding_model_id
    )
    if not rows:
        return None
    return np.asarray(rows[0].embedding, dtype=np.float32)


def _get_text_similarities(
    session: Session,
    annotation_collection_id: UUID,
    embedding_model_id: UUID,
    labels: Sequence[AnnotationLabelTable],
    crop_embedding: NDArray[np.float32],
) -> dict[UUID, float]:
    """Compute the cosine similarity of the crop to the text anchor of each class.

    Returns:
        Similarity per class ID. Empty when the embedding space cannot embed text.
    """
    try:
        text_embedder = default_embedder.resolve_query_embedder(
            session=session,
            collection_id=annotation_collection_id,
            embedder_type=TextEmbedder,
        )
    except MissingCapabilityError:
        return {}

    missing_names = sorted(
        {
            label.annotation_label_name
            for label in labels
            if (embedding_model_id, label.annotation_label_name) not in _text_anchor_cache
        }
    )
    if missing_names:
        result = text_embedder.embed_text(
            texts=[TEXT_ANCHOR_PROMPT.format(class_name=name) for name in missing_names]
        )
        for index, embedding in zip(result.kept_indices, result.embeddings):
            _text_anchor_cache[(embedding_model_id, missing_names[index])] = _normalize(
                vector=np.asarray(embedding, dtype=np.float32)
            )

    normalized_crop = _normalize(vector=crop_embedding)
    similarities: dict[UUID, float] = {}
    for label in labels:
        anchor = _text_anchor_cache.get((embedding_model_id, label.annotation_label_name))
        if anchor is not None:
            similarities[label.annotation_label_id] = float(np.dot(normalized_crop, anchor))
    return similarities


def _normalize(vector: NDArray[np.float32]) -> NDArray[np.float32]:
    norm = np.linalg.norm(vector)
    if norm == 0.0:
        return vector
    normalized: NDArray[np.float32] = vector / norm
    return normalized
