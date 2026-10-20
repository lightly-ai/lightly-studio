from __future__ import annotations

import numpy as np
import pytest
from labelformat.model.binary_mask_segmentation import BinaryMaskSegmentation
from labelformat.model.bounding_box import BoundingBox

from lightly_studio.assisted_labeling.provider import Prediction, ProviderError
from lightly_studio.models.assisted_labeling import AnnotationPreview, AnnotationPreviewBox
from lightly_studio.services.assisted_labeling_service import to_annotation_preview


def test_to_sorted_annotation_previews() -> None:
    empty_mask = np.zeros((2, 2), dtype=np.bool_)
    left_mask = np.array([[1, 0], [0, 0]], dtype=np.bool_)
    right_mask = np.array([[0, 1], [0, 0]], dtype=np.bool_)
    bottom_mask = np.array([[0, 0], [1, 0]], dtype=np.bool_)
    predictions = [
        Prediction(mask=left_mask, score=None),
        Prediction(mask=right_mask, score=0.5),
        Prediction(mask=empty_mask, score=1.0),
        Prediction(mask=bottom_mask, score=0.9),
    ]

    previews = to_annotation_preview.to_sorted_annotation_previews(
        predictions=predictions, width=2, height=2
    )

    assert [(preview.bbox.x, preview.bbox.y, preview.score) for preview in previews] == [
        (0, 1, 0.9),
        (1, 0, 0.5),
        (0, 0, None),
    ]


def test_to_sorted_annotation_previews__low_score_before_none() -> None:
    left_mask = np.array([[1, 0], [0, 0]], dtype=np.bool_)
    right_mask = np.array([[0, 1], [0, 0]], dtype=np.bool_)
    predictions = [
        Prediction(mask=left_mask, score=None),
        Prediction(mask=right_mask, score=-2.0),
    ]

    previews = to_annotation_preview.to_sorted_annotation_previews(
        predictions=predictions, width=2, height=2
    )

    assert [preview.score for preview in previews] == [-2.0, None]


def test_to_annotation_preview() -> None:
    mask = np.array(
        [
            [0, 0, 0, 0],
            [0, 1, 1, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
        ],
        dtype=np.bool_,
    )
    prediction = Prediction(mask=mask, score=0.8)

    preview = to_annotation_preview._to_annotation_preview(prediction=prediction, width=4, height=5)

    assert preview == AnnotationPreview(
        bbox=AnnotationPreviewBox(x=1, y=1, width=2, height=2),
        segmentation_mask=[5, 2, 3, 1, 9],
        score=0.8,
    )


def test_to_annotation_preview__round_trip() -> None:
    mask = np.zeros((5, 4), dtype=np.bool_)
    mask[1, 1:3] = True
    mask[2, 2] = True
    mask[4, 0] = True
    prediction = Prediction(mask=mask, score=None)

    preview = to_annotation_preview._to_annotation_preview(prediction=prediction, width=4, height=5)

    assert preview is not None
    decoded = BinaryMaskSegmentation.from_rle(
        rle_row_wise=preview.segmentation_mask,
        width=4,
        height=5,
        bounding_box=BoundingBox(xmin=0, ymin=0, xmax=4, ymax=5),
    ).get_binary_mask()
    assert np.array_equal(decoded.astype(np.bool_), mask)


def test_to_annotation_preview__empty_mask() -> None:
    prediction = Prediction(mask=np.zeros((3, 4), dtype=np.bool_), score=None)

    preview = to_annotation_preview._to_annotation_preview(prediction=prediction, width=4, height=3)

    assert preview is None


def test_to_annotation_preview__wrong_shape() -> None:
    prediction = Prediction(mask=np.ones((4, 3), dtype=np.bool_), score=None)

    with pytest.raises(ProviderError, match=r"expected \(3, 4\)"):
        to_annotation_preview._to_annotation_preview(prediction=prediction, width=4, height=3)
