"""Scores annotation classes from crop neighbours and text anchors."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import UUID

from lightly_studio.resolvers.annotation_resolver import AnnotationNeighbour

TEXT_ANCHOR_WEIGHT = 3.0
"""Weight of one text anchor relative to one crop neighbour.

Crop-to-crop similarity is about 0.7-0.9 and text-to-crop similarity about 0.2-0.35, so a weight
of 3 makes one anchor worth about one neighbour.
"""


def score_classes(
    label_ids: Sequence[UUID],
    neighbours: Sequence[AnnotationNeighbour],
    text_similarities: Mapping[UUID, float],
    text_anchor_weight: float = TEXT_ANCHOR_WEIGHT,
) -> dict[UUID, float]:
    """Scores each class by its crop neighbours and its text anchor.

    The raw score of a class is the sum of the similarities of its neighbours plus
    `text_anchor_weight` times the similarity of its text anchor. Raw scores are then normalized
    to sum to 1.

    Args:
        label_ids: Every class to score. The result has one entry per ID.
        neighbours: The nearest labeled crops of the annotation being predicted.
        text_similarities: Similarity of the annotation's crop to each class's text anchor.
            Classes without an anchor are missing from the mapping.
        text_anchor_weight: Weight of one text anchor relative to one crop neighbour.

    Returns:
        One score per ID in `label_ids`. The scores sum to 1, or are all 0 when no class has
        any evidence.
    """
    raw_scores = {
        label_id: text_anchor_weight * text_similarities.get(label_id, 0.0)
        for label_id in label_ids
    }
    for neighbour in neighbours:
        # A neighbour whose class is not scored, for example a deleted class, is dropped.
        if neighbour.annotation_label_id in raw_scores:
            raw_scores[neighbour.annotation_label_id] += neighbour.similarity

    clipped_scores = {label_id: max(score, 0.0) for label_id, score in raw_scores.items()}
    total = sum(clipped_scores.values())
    if total == 0.0:
        return clipped_scores
    return {label_id: score / total for label_id, score in clipped_scores.items()}
