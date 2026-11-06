from __future__ import annotations

import uuid

import numpy as np
import pytest

from lightly_studio.assisted_labeling.labeling_model import LabelingImage, PredictedAnnotation
from lightly_studio.assisted_labeling.provider import ProviderError
from lightly_studio.models.assisted_labeling import AnnotationPreviewBox, ModelAnnotationRequest
from lightly_studio.services import assisted_labeling_service
from tests.assisted_labeling import helpers
from tests.services.assisted_labeling_service.helpers import StubLabelingModel

BOX = (0.0, 0.0, 4.0, 2.0)


def test_create_model_preview__boxes() -> None:
    model = StubLabelingModel(
        predictions=[
            PredictedAnnotation(class_name="cat", box=BOX, score=0.5),
            PredictedAnnotation(class_name="dog", box=(1.0, 0.0, 3.0, 1.0), score=0.9),
        ]
    )
    image = helpers.make_image(width=4, height=2)

    response = assisted_labeling_service.create_model_preview(
        model=model,
        image=image,
        request=_request(image=image, threshold=0.4),
        user_email=None,
    )

    assert model.thresholds == [0.4]
    assert [(p.class_name, p.bbox, p.segmentation_mask, p.score) for p in response.predictions] == [
        ("dog", AnnotationPreviewBox(x=1, y=0, width=2, height=1), None, 0.9),
        ("cat", AnnotationPreviewBox(x=0, y=0, width=4, height=2), None, 0.5),
    ]


def test_create_model_preview__drops_scores_below_threshold() -> None:
    model = StubLabelingModel(
        predictions=[
            PredictedAnnotation(class_name="cat", box=BOX, score=0.39),
            PredictedAnnotation(class_name="cat", box=BOX, score=0.4),
        ]
    )
    image = helpers.make_image(width=4, height=2)

    response = assisted_labeling_service.create_model_preview(
        model=model, image=image, request=_request(image=image, threshold=0.4), user_email=None
    )

    assert [preview.score for preview in response.predictions] == [0.4]


def test_create_model_preview__keeps_requested_classes() -> None:
    model = StubLabelingModel(
        predictions=[
            PredictedAnnotation(class_name="cat", box=BOX, score=0.8),
            PredictedAnnotation(class_name="dog", box=BOX, score=0.8),
            PredictedAnnotation(class_name="bird", box=BOX, score=0.8),
        ]
    )
    image = helpers.make_image(width=4, height=2)

    response = assisted_labeling_service.create_model_preview(
        model=model,
        image=image,
        request=_request(image=image, class_names=["cat", "bird"]),
        user_email=None,
    )

    assert [preview.class_name for preview in response.predictions] == ["cat", "bird"]


def test_create_model_preview__clamps_box_to_image() -> None:
    model = StubLabelingModel(
        predictions=[PredictedAnnotation(class_name="cat", box=(-1.5, 0.2, 2.5, 9.0), score=0.8)]
    )
    image = helpers.make_image(width=4, height=2)

    response = assisted_labeling_service.create_model_preview(
        model=model, image=image, request=_request(image=image), user_email=None
    )

    (preview,) = response.predictions
    assert preview.bbox == AnnotationPreviewBox(x=0, y=0, width=3, height=2)


def test_create_model_preview__keeps_empty_box_one_pixel() -> None:
    model = StubLabelingModel(
        predictions=[PredictedAnnotation(class_name="cat", box=(2.0, 1.0, 2.0, 1.0), score=0.8)]
    )
    image = helpers.make_image(width=4, height=2)

    response = assisted_labeling_service.create_model_preview(
        model=model, image=image, request=_request(image=image), user_email=None
    )

    (preview,) = response.predictions
    assert preview.bbox == AnnotationPreviewBox(x=2, y=1, width=1, height=1)


def test_create_model_preview__box_not_finite() -> None:
    model = StubLabelingModel(
        predictions=[
            PredictedAnnotation(class_name="cat", box=(0.0, 0.0, float("nan"), 1.0), score=0.8)
        ]
    )
    image = helpers.make_image(width=4, height=2)

    with pytest.raises(ProviderError, match="not finite"):
        assisted_labeling_service.create_model_preview(
            model=model, image=image, request=_request(image=image), user_email=None
        )


def test_create_model_preview__mask_defines_box() -> None:
    mask = np.zeros((2, 4), dtype=np.bool_)
    mask[1, 2:4] = True
    model = StubLabelingModel(
        predictions=[PredictedAnnotation(class_name="cat", box=BOX, mask=mask, score=0.8)]
    )
    image = helpers.make_image(width=4, height=2)

    response = assisted_labeling_service.create_model_preview(
        model=model, image=image, request=_request(image=image), user_email=None
    )

    (preview,) = response.predictions
    assert preview.bbox == AnnotationPreviewBox(x=2, y=1, width=2, height=1)
    assert preview.segmentation_mask == [6, 2]


def test_create_model_preview__drops_empty_mask() -> None:
    model = StubLabelingModel(
        predictions=[
            PredictedAnnotation(
                class_name="cat", box=BOX, mask=np.zeros((2, 4), dtype=np.bool_), score=0.8
            )
        ]
    )
    image = helpers.make_image(width=4, height=2)

    response = assisted_labeling_service.create_model_preview(
        model=model, image=image, request=_request(image=image), user_email=None
    )

    assert response.predictions == []


def test_create_model_preview__limits_instances() -> None:
    model = StubLabelingModel(
        predictions=[
            PredictedAnnotation(class_name="cat", box=BOX, score=score) for score in (0.6, 0.8)
        ]
    )
    image = helpers.make_image(width=4, height=2)

    response = assisted_labeling_service.create_model_preview(
        model=model,
        image=image,
        request=_request(image=image, max_instances=1),
        user_email=None,
    )

    assert [preview.score for preview in response.predictions] == [0.8]


def test_create_model_preview__wrong_mask_shape() -> None:
    model = StubLabelingModel(
        predictions=[
            PredictedAnnotation(
                class_name="cat", box=BOX, mask=np.ones((4, 2), dtype=np.bool_), score=0.8
            )
        ]
    )
    image = helpers.make_image(width=4, height=2)

    with pytest.raises(ProviderError, match=r"shape \(4, 2\)"):
        assisted_labeling_service.create_model_preview(
            model=model, image=image, request=_request(image=image), user_email=None
        )


def _request(
    image: LabelingImage,
    threshold: float = 0.5,
    max_instances: int = 100,
    class_names: list[str] | None = None,
) -> ModelAnnotationRequest:
    return ModelAnnotationRequest(
        collection_id=uuid.uuid4(),
        sample_id=image.sample_id,
        model_id="model",
        threshold=threshold,
        max_instances=max_instances,
        class_names=class_names,
    )
