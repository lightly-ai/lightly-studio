from __future__ import annotations

from uuid import UUID

import pytest

from lightly_studio.resolvers.annotation_resolver import AnnotationNeighbour
from lightly_studio.services.annotations_service import class_prediction_scoring

CAT = UUID(int=1)
DOG = UUID(int=2)
BUS = UUID(int=3)


def test_score_classes__knn_only() -> None:
    scores = class_prediction_scoring.score_classes(
        label_ids=[CAT, DOG],
        neighbours=[
            AnnotationNeighbour(annotation_label_id=CAT, similarity=0.9),
            AnnotationNeighbour(annotation_label_id=CAT, similarity=0.8),
            AnnotationNeighbour(annotation_label_id=DOG, similarity=0.7),
        ],
        text_similarities={},
    )

    assert scores == {CAT: pytest.approx(1.7 / 2.4), DOG: pytest.approx(0.7 / 2.4)}


def test_score_classes__text_only() -> None:
    scores = class_prediction_scoring.score_classes(
        label_ids=[CAT, DOG],
        neighbours=[],
        text_similarities={CAT: 0.3, DOG: 0.1},
    )

    assert scores == {CAT: pytest.approx(0.75), DOG: pytest.approx(0.25)}


def test_score_classes__blends_text_and_knn() -> None:
    # Raw scores: cat 0.8 + 3 * 0.2 = 1.4, dog 3 * 0.3 = 0.9.
    scores = class_prediction_scoring.score_classes(
        label_ids=[CAT, DOG],
        neighbours=[AnnotationNeighbour(annotation_label_id=CAT, similarity=0.8)],
        text_similarities={CAT: 0.2, DOG: 0.3},
        text_anchor_weight=3.0,
    )

    assert scores == {CAT: pytest.approx(1.4 / 2.3), DOG: pytest.approx(0.9 / 2.3)}


def test_score_classes__no_evidence_returns_all_zero() -> None:
    scores = class_prediction_scoring.score_classes(
        label_ids=[CAT, DOG],
        neighbours=[],
        text_similarities={},
    )

    assert scores == {CAT: 0.0, DOG: 0.0}


def test_score_classes__returns_every_label() -> None:
    scores = class_prediction_scoring.score_classes(
        label_ids=[CAT, DOG, BUS],
        neighbours=[AnnotationNeighbour(annotation_label_id=DOG, similarity=0.5)],
        text_similarities={},
    )

    assert scores == {CAT: 0.0, DOG: pytest.approx(1.0), BUS: 0.0}
