from __future__ import annotations

from uuid import UUID

import numpy as np
import pytest
from lightly_studio_serve.labeling_model import ModelTask
from lightly_studio_serve.types import PredictedAnnotation

from lightly_studio.assisted_labeling.labeling_model_runner import LocalLabelingModelRunner
from lightly_studio.assisted_labeling.provider import ProviderError
from lightly_studio.models.assisted_labeling import (
    AnnotationPreviewBox,
    ModelAnnotationRequest,
    ModelAnnotationResponse,
)
from lightly_studio.services import assisted_labeling_service
from tests.assisted_labeling import helpers
from tests.assisted_labeling.helpers import StubLabelingModel

COLLECTION_ID = UUID(int=7)
WIDTH = 4
HEIGHT = 2


def test_create_model_preview__boxes() -> None:
    model = StubLabelingModel(
        model_id="m",
        class_names=["cat", "dog"],
        predictions=[
            PredictedAnnotation(class_name="cat", box=(0.0, 0.0, 4.0, 2.0), score=0.5),
            PredictedAnnotation(class_name="dog", box=(1.0, 0.0, 3.0, 1.0), score=0.9),
        ],
    )

    response = _create_model_preview(model=model, threshold=0.4)

    assert model.thresholds == [0.4]
    assert [(p.class_name, p.bbox, p.segmentation_mask, p.score) for p in response.predictions] == [
        ("dog", AnnotationPreviewBox(x=1, y=0, width=2, height=1), None, 0.9),
        ("cat", AnnotationPreviewBox(x=0, y=0, width=4, height=2), None, 0.5),
    ]


def test_create_model_preview__drops_scores_below_threshold() -> None:
    model = StubLabelingModel(
        model_id="m",
        class_names=["cat"],
        predictions=[
            PredictedAnnotation(class_name="cat", box=(0.0, 0.0, 4.0, 2.0), score=0.39),
            PredictedAnnotation(class_name="cat", box=(0.0, 0.0, 4.0, 2.0), score=0.4),
        ],
    )

    response = _create_model_preview(model=model, threshold=0.4)

    assert [preview.score for preview in response.predictions] == [0.4]


def test_create_model_preview__box_contains_float_box() -> None:
    model = StubLabelingModel(
        model_id="m",
        class_names=["cat"],
        predictions=[PredictedAnnotation(class_name="cat", box=(0.5, 0.2, 2.1, 1.5), score=0.8)],
    )

    response = _create_model_preview(model=model, threshold=0.4)

    assert [preview.bbox for preview in response.predictions] == [
        AnnotationPreviewBox(x=0, y=0, width=3, height=2)
    ]


def test_create_model_preview__clamps_box_to_image() -> None:
    model = StubLabelingModel(
        model_id="m",
        class_names=["cat"],
        predictions=[PredictedAnnotation(class_name="cat", box=(-3.0, -1.0, 9.0, 5.0), score=0.8)],
    )

    response = _create_model_preview(model=model, threshold=0.4)

    assert [preview.bbox for preview in response.predictions] == [
        AnnotationPreviewBox(x=0, y=0, width=4, height=2)
    ]


def test_create_model_preview__mask_defines_box() -> None:
    mask = np.zeros((HEIGHT, WIDTH), dtype=np.bool_)
    mask[1, 1:3] = True
    model = StubLabelingModel(
        model_id="m",
        task=ModelTask.INSTANCE_SEGMENTATION,
        class_names=["cat"],
        predictions=[
            PredictedAnnotation(class_name="cat", box=(0.0, 0.0, 4.0, 2.0), score=0.8, mask=mask)
        ],
    )

    response = _create_model_preview(model=model, threshold=0.4)

    (preview,) = response.predictions
    assert preview.bbox == AnnotationPreviewBox(x=1, y=1, width=2, height=1)
    # Row-wise run lengths that start with the background: 5 off, 2 on, 1 off.
    assert preview.segmentation_mask == [5, 2, 1]


def test_create_model_preview__drops_empty_mask() -> None:
    model = StubLabelingModel(
        model_id="m",
        task=ModelTask.INSTANCE_SEGMENTATION,
        class_names=["cat"],
        predictions=[
            PredictedAnnotation(
                class_name="cat",
                box=(0.0, 0.0, 4.0, 2.0),
                score=0.8,
                mask=np.zeros((HEIGHT, WIDTH), dtype=np.bool_),
            )
        ],
    )

    response = _create_model_preview(model=model, threshold=0.4)

    assert response.predictions == []


def test_create_model_preview__limits_previews() -> None:
    # 301 predictions with the scores 0.400, 0.401, ..., 0.700.
    model = StubLabelingModel(
        model_id="m",
        class_names=["cat"],
        predictions=[
            PredictedAnnotation(
                class_name="cat", box=(0.0, 0.0, 4.0, 2.0), score=(400 + index) / 1000
            )
            for index in range(301)
        ],
    )

    response = _create_model_preview(model=model, threshold=0.4)

    # The limit is 300, so the lowest score 0.4 is dropped.
    assert len(response.predictions) == 300
    assert response.predictions[0].score == 0.7
    assert response.predictions[-1].score == 0.401


@pytest.mark.parametrize(
    ("prediction", "message"),
    [
        pytest.param(
            PredictedAnnotation(class_name="cat", box=(0.0, 0.0, 4.0, 2.0), score=float("nan")),
            r"the score nan",
            id="score-nan",
        ),
        pytest.param(
            PredictedAnnotation(class_name="cat", box=(0.0, 0.0, 4.0, 2.0), score=1.5),
            r"the score 1\.5",
            id="score-above-1",
        ),
        pytest.param(
            PredictedAnnotation(class_name="cat", box=(0.0, 0.0, 4.0, 2.0), score=-0.1),
            r"the score -0\.1",
            id="score-below-0",
        ),
        pytest.param(
            PredictedAnnotation(class_name="dog", box=(0.0, 0.0, 4.0, 2.0), score=0.8),
            r"the class 'dog', which is not one of its class names",
            id="unknown-class",
        ),
        pytest.param(
            PredictedAnnotation(class_name="cat", box=(0.0, 0.0, float("inf"), 2.0), score=0.8),
            r"a value that is not finite",
            id="box-not-finite",
        ),
        pytest.param(
            PredictedAnnotation(class_name="cat", box=(3.0, 0.0, 1.0, 2.0), score=0.8),
            r"a positive size",
            id="box-inverted",
        ),
        pytest.param(
            PredictedAnnotation(class_name="cat", box=(1.0, 1.0, 3.0, 1.0), score=0.8),
            r"a positive size",
            id="box-empty",
        ),
        pytest.param(
            PredictedAnnotation(
                class_name="cat",
                box=(0.0, 0.0, 4.0, 2.0),
                score=0.8,
                mask=np.ones((WIDTH, HEIGHT), dtype=np.bool_),
            ),
            r"a mask of shape \(4, 2\), expected \(2, 4\)",
            id="mask-shape",
        ),
        pytest.param(
            PredictedAnnotation(
                class_name="cat",
                box=(0.0, 0.0, 4.0, 2.0),
                score=0.8,
                mask=np.ones((HEIGHT, WIDTH), dtype=np.float32),
            ),
            r"a mask of dtype float32, expected bool",
            id="mask-dtype",
        ),
    ],
)
def test_create_model_preview__invalid_prediction(
    prediction: PredictedAnnotation, message: str
) -> None:
    model = StubLabelingModel(model_id="m", class_names=["cat"], predictions=[prediction])

    with pytest.raises(ProviderError, match=message):
        _create_model_preview(model=model, threshold=0.4)


def test_create_model_preview__invalid_prediction_below_threshold() -> None:
    model = StubLabelingModel(
        model_id="m",
        class_names=["cat"],
        predictions=[PredictedAnnotation(class_name="dog", box=(0.0, 0.0, 4.0, 2.0), score=0.1)],
    )

    with pytest.raises(ProviderError, match=r"the class 'dog'"):
        _create_model_preview(model=model, threshold=0.4)


def _create_model_preview(model: StubLabelingModel, threshold: float) -> ModelAnnotationResponse:
    image = helpers.make_image(
        width=WIDTH, height=HEIGHT, data=helpers.png_bytes(width=WIDTH, height=HEIGHT)
    )
    return assisted_labeling_service.create_model_preview(
        runner=LocalLabelingModelRunner(model=model),
        image=image,
        request=ModelAnnotationRequest(
            collection_id=COLLECTION_ID,
            sample_id=image.sample_id,
            model_id=model.model_id,
            threshold=threshold,
        ),
    )
