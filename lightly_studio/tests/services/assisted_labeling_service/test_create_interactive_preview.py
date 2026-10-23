from __future__ import annotations

import uuid

import numpy as np

from lightly_studio.assisted_labeling.provider import (
    BoxPrompt,
    PointPrompt,
    Prediction,
    ProviderImage,
)
from lightly_studio.models.assisted_labeling import (
    AnnotationBox,
    AnnotationPoint,
    AnnotationPreviewBox,
    InteractiveAnnotationRequest,
)
from lightly_studio.services import assisted_labeling_service
from tests.assisted_labeling import helpers
from tests.services.assisted_labeling_service.helpers import StubProvider


def test_create_interactive_preview__points() -> None:
    mask = np.zeros((50, 100), dtype=np.bool_)
    mask[20:31, 45:56] = True
    provider = StubProvider(predictions=[Prediction(mask=mask, score=0.9)])
    image = helpers.make_image(width=100, height=50)

    response = assisted_labeling_service.create_interactive_preview(
        provider=provider,
        image=image,
        request=_request(image=image, points=[AnnotationPoint(x=0.5, y=0.5, positive=True)]),
    )

    assert response.prediction is not None
    assert response.prediction.bbox == AnnotationPreviewBox(x=45, y=20, width=11, height=11)
    assert response.prediction.score == 0.9


def test_create_interactive_preview__point_prompt() -> None:
    provider = StubProvider()
    image = helpers.make_image(width=100, height=50)

    assisted_labeling_service.create_interactive_preview(
        provider=provider,
        image=image,
        request=_request(
            image=image,
            points=[
                AnnotationPoint(x=0.5, y=0.5, positive=True),
                AnnotationPoint(x=0.1, y=0.2, positive=False),
            ],
        ),
    )

    (prompt,) = provider.prompts
    assert prompt.points == [
        PointPrompt(x=50, y=25, positive=True),
        PointPrompt(x=10, y=10, positive=False),
    ]
    assert prompt.boxes == []
    assert prompt.text is None
    assert prompt.max_masks == 1


def test_create_interactive_preview__box_prompt() -> None:
    provider = StubProvider()
    image = helpers.make_image(width=100, height=50)

    assisted_labeling_service.create_interactive_preview(
        provider=provider,
        image=image,
        request=_request(image=image, boxes=[AnnotationBox(x=0.1, y=0.2, width=0.4, height=0.6)]),
    )

    (prompt,) = provider.prompts
    assert prompt.boxes == [BoxPrompt(x_min=10, y_min=10, x_max=50, y_max=40)]
    assert prompt.points == []
    assert prompt.max_masks == 1


def test_create_interactive_preview__no_mask() -> None:
    image = helpers.make_image(width=100, height=50)

    response = assisted_labeling_service.create_interactive_preview(
        provider=StubProvider(predictions=[]),
        image=image,
        request=_request(image=image, points=[AnnotationPoint(x=0.5, y=0.5, positive=True)]),
    )

    assert response.prediction is None


def test_create_interactive_preview__highest_score() -> None:
    low_mask = np.zeros((2, 4), dtype=np.bool_)
    low_mask[0, 0] = True
    high_mask = np.zeros((2, 4), dtype=np.bool_)
    high_mask[1, 3] = True
    provider = StubProvider(
        predictions=[
            Prediction(mask=low_mask, score=0.3),
            Prediction(mask=high_mask, score=0.7),
        ]
    )
    image = helpers.make_image(width=4, height=2)

    response = assisted_labeling_service.create_interactive_preview(
        provider=provider,
        image=image,
        request=_request(image=image, points=[AnnotationPoint(x=0.5, y=0.5, positive=True)]),
    )

    assert response.prediction is not None
    assert response.prediction.score == 0.7
    assert response.prediction.bbox == AnnotationPreviewBox(x=3, y=1, width=1, height=1)


def _request(
    image: ProviderImage,
    points: list[AnnotationPoint] | None = None,
    boxes: list[AnnotationBox] | None = None,
) -> InteractiveAnnotationRequest:
    return InteractiveAnnotationRequest(
        collection_id=uuid.uuid4(), sample_id=image.sample_id, points=points, boxes=boxes
    )
