from __future__ import annotations

import numpy as np
import pytest

from lightly_studio.assisted_labeling.provider import Prediction, ProviderError
from lightly_studio.models.assisted_labeling import AnnotationPreview, AnnotationPreviewBox
from lightly_studio.services.assisted_labeling_service import to_annotation_preview


def test_to_annotation_preview() -> None:
    mask = np.array(
        [
            [0, 0, 0, 0],
            [0, 1, 1, 0],
            [0, 0, 1, 0],
        ],
        dtype=np.bool_,
    )
    prediction = Prediction(mask=mask, score=0.8, class_name="dog")

    preview = to_annotation_preview.to_annotation_preview(prediction=prediction, width=4, height=3)

    assert preview == AnnotationPreview(
        bbox=AnnotationPreviewBox(x=1, y=1, width=2, height=2),
        segmentation_mask=[0, 2, 1, 1],
        score=0.8,
        class_name="dog",
    )


def test_to_annotation_preview__empty_mask() -> None:
    prediction = Prediction(mask=np.zeros((3, 4), dtype=np.bool_), score=None, class_name=None)

    preview = to_annotation_preview.to_annotation_preview(prediction=prediction, width=4, height=3)

    assert preview is None


def test_to_annotation_preview__wrong_shape() -> None:
    prediction = Prediction(mask=np.ones((4, 3), dtype=np.bool_), score=None, class_name=None)

    with pytest.raises(ProviderError, match=r"expected \(3, 4\)"):
        to_annotation_preview.to_annotation_preview(prediction=prediction, width=4, height=3)


def test_to_sorted_annotation_previews() -> None:
    empty_mask = np.zeros((2, 2), dtype=np.bool_)
    left_mask = np.array([[1, 0], [0, 0]], dtype=np.bool_)
    right_mask = np.array([[0, 1], [0, 0]], dtype=np.bool_)
    bottom_mask = np.array([[0, 0], [1, 0]], dtype=np.bool_)
    predictions = [
        Prediction(mask=left_mask, score=None, class_name="no score"),
        Prediction(mask=right_mask, score=0.5, class_name="low"),
        Prediction(mask=empty_mask, score=1.0, class_name="empty"),
        Prediction(mask=bottom_mask, score=0.9, class_name="high"),
    ]

    previews = to_annotation_preview.to_sorted_annotation_previews(
        predictions=predictions, width=2, height=2
    )

    assert [preview.class_name for preview in previews] == ["high", "low", "no score"]
