from __future__ import annotations

from uuid import uuid4

import numpy as np

from lightly_studio.assisted_labeling.provider import BoxPrompt, Prediction, ProviderImage
from lightly_studio.models.assisted_labeling import (
    AnnotationBox,
    AnnotationPreviewBox,
    InstancesAnnotationRequest,
)
from lightly_studio.services import assisted_labeling_service
from tests.assisted_labeling import helpers
from tests.services.assisted_labeling_service.helpers import StubProvider


def test_create_instances_preview__text() -> None:
    provider = StubProvider(
        predictions=[
            _prediction(x=0, score=0.5),
            _prediction(x=2, score=0.9),
        ]
    )
    image = helpers.make_image(width=4, height=2)

    response = assisted_labeling_service.create_instances_preview(
        provider=provider,
        image=image,
        request=_request(image=image, prompt=" dog ", max_instances=2),
    )

    (prompt,) = provider.prompts
    assert prompt.text == "dog"
    assert prompt.max_masks == 2
    assert prompt.points == []
    assert prompt.boxes == []
    assert [prediction.bbox for prediction in response.predictions] == [
        AnnotationPreviewBox(x=2, y=0, width=1, height=1),
        AnnotationPreviewBox(x=0, y=0, width=1, height=1),
    ]
    assert [prediction.score for prediction in response.predictions] == [0.9, 0.5]


def test_create_instances_preview__boxes() -> None:
    provider = StubProvider()
    image = helpers.make_image(width=100, height=50)

    assisted_labeling_service.create_instances_preview(
        provider=provider,
        image=image,
        request=_request(
            image=image,
            boxes=[AnnotationBox(x=0.1, y=0.2, width=0.4, height=0.6)],
            max_instances=10,
        ),
    )

    (prompt,) = provider.prompts
    assert prompt.boxes == [BoxPrompt(x_min=10, y_min=10, x_max=50, y_max=40)]
    assert prompt.text is None
    assert prompt.points == []
    assert prompt.max_masks == 10


def test_create_instances_preview__max_instances() -> None:
    provider = StubProvider(
        predictions=[
            _prediction(x=0, score=0.9),
            _prediction(x=1, score=0.8),
            _prediction(x=2, score=0.7),
        ]
    )
    image = helpers.make_image(width=4, height=2)

    response = assisted_labeling_service.create_instances_preview(
        provider=provider,
        image=image,
        request=_request(image=image, prompt="dog", max_instances=2),
    )

    assert [prediction.score for prediction in response.predictions] == [0.9, 0.8]


def _prediction(x: int, score: float) -> Prediction:
    # A single pixel at (x, 0) of a 4x2 image.
    mask = np.zeros((2, 4), dtype=np.bool_)
    mask[0, x] = True
    return Prediction(mask=mask, score=score)


def _request(
    image: ProviderImage,
    prompt: str | None = None,
    boxes: list[AnnotationBox] | None = None,
    max_instances: int = 16,
) -> InstancesAnnotationRequest:
    return InstancesAnnotationRequest(
        collection_id=uuid4(),
        sample_id=image.sample_id,
        prompt=prompt,
        boxes=boxes,
        max_instances=max_instances,
    )
