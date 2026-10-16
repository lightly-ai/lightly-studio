from __future__ import annotations

from uuid import uuid4

import numpy as np
from pytest_mock import MockerFixture

from lightly_studio.assisted_labeling.fake_provider import FakeProvider
from lightly_studio.assisted_labeling.provider import Prediction, ProviderImage
from lightly_studio.models.assisted_labeling import (
    AnnotationBox,
    AnnotationPoint,
    AnnotationPreviewBox,
    InteractiveAnnotationRequest,
)
from lightly_studio.services import assisted_labeling_service


def test_create_interactive_preview__points() -> None:
    image = _image(width=100, height=50)

    response = assisted_labeling_service.create_interactive_preview(
        provider=FakeProvider(),
        image=image,
        request=_request(image=image, points=[AnnotationPoint(x=0.5, y=0.5, positive=True)]),
    )

    # The fake provider returns a disk with radius 5 around the pixel (50, 25).
    assert response.prediction is not None
    assert response.prediction.bbox == AnnotationPreviewBox(x=45, y=20, width=11, height=11)
    assert response.prediction.score == 0.9
    assert response.prediction.class_name is None


def test_create_interactive_preview__boxes() -> None:
    image = _image(width=100, height=50)

    response = assisted_labeling_service.create_interactive_preview(
        provider=FakeProvider(),
        image=image,
        request=_request(image=image, boxes=[AnnotationBox(x=0.1, y=0.2, width=0.4, height=0.6)]),
    )

    # The fake provider returns an ellipse inside the pixel box (10, 10, 50, 40).
    assert response.prediction is not None
    assert response.prediction.bbox == AnnotationPreviewBox(x=10, y=10, width=41, height=31)


def test_create_interactive_preview__prompt(mocker: MockerFixture) -> None:
    provider = FakeProvider()
    spy_segment = mocker.spy(provider, "segment")
    image = _image(width=100, height=50)

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

    prompt = spy_segment.call_args.kwargs["prompt"]
    assert [(point.x, point.y, point.positive) for point in prompt.points] == [
        (50, 25, True),
        (10, 10, False),
    ]
    assert prompt.boxes == []
    assert prompt.text is None
    assert prompt.max_masks == 1


def test_create_interactive_preview__no_mask(mocker: MockerFixture) -> None:
    provider = FakeProvider()
    mocker.patch.object(provider, "segment", return_value=[])
    image = _image(width=100, height=50)

    response = assisted_labeling_service.create_interactive_preview(
        provider=provider,
        image=image,
        request=_request(image=image, points=[AnnotationPoint(x=0.5, y=0.5, positive=True)]),
    )

    assert response.prediction is None


def test_create_interactive_preview__highest_score(mocker: MockerFixture) -> None:
    low_mask = np.zeros((2, 4), dtype=np.bool_)
    low_mask[0, 0] = True
    high_mask = np.zeros((2, 4), dtype=np.bool_)
    high_mask[1, 3] = True
    provider = FakeProvider()
    mocker.patch.object(
        provider,
        "segment",
        return_value=[
            Prediction(mask=low_mask, score=0.3, class_name=None),
            Prediction(mask=high_mask, score=0.7, class_name=None),
        ],
    )
    image = _image(width=4, height=2)

    response = assisted_labeling_service.create_interactive_preview(
        provider=provider,
        image=image,
        request=_request(image=image, points=[AnnotationPoint(x=0.5, y=0.5, positive=True)]),
    )

    assert response.prediction is not None
    assert response.prediction.score == 0.7
    assert response.prediction.bbox == AnnotationPreviewBox(x=3, y=1, width=1, height=1)


def _image(width: int, height: int) -> ProviderImage:
    return ProviderImage(
        sample_id=uuid4(), width=width, height=height, file_name="img.png", read_bytes=lambda: b""
    )


def _request(
    image: ProviderImage,
    points: list[AnnotationPoint] | None = None,
    boxes: list[AnnotationBox] | None = None,
) -> InteractiveAnnotationRequest:
    return InteractiveAnnotationRequest(
        collection_id=uuid4(), sample_id=image.sample_id, points=points, boxes=boxes
    )
