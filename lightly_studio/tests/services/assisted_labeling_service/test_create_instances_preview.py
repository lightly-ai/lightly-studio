from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError
from pytest_mock import MockerFixture

from lightly_studio.assisted_labeling.fake_provider import FakeProvider
from lightly_studio.assisted_labeling.provider import ProviderImage
from lightly_studio.models.assisted_labeling import (
    AnnotationBox,
    AnnotationPreviewBox,
    InstancesAnnotationRequest,
)
from lightly_studio.services import assisted_labeling_service


def test_create_instances_preview__text() -> None:
    image = _image(width=100, height=50)

    response = assisted_labeling_service.create_instances_preview(
        provider=FakeProvider(),
        image=image,
        request=_request(image=image, prompt=" dog ", max_instances=2),
    )

    # The fake provider returns disks with radius 5 around (25, 25) and (50, 25).
    assert [prediction.bbox for prediction in response.predictions] == [
        AnnotationPreviewBox(x=20, y=20, width=11, height=11),
        AnnotationPreviewBox(x=45, y=20, width=11, height=11),
    ]
    assert [prediction.class_name for prediction in response.predictions] == ["dog", "dog"]


def test_create_instances_preview__boxes(mocker: MockerFixture) -> None:
    provider = FakeProvider()
    spy_segment = mocker.spy(provider, "segment")
    image = _image(width=100, height=50)

    response = assisted_labeling_service.create_instances_preview(
        provider=provider,
        image=image,
        request=_request(
            image=image,
            boxes=[AnnotationBox(x=0.1, y=0.2, width=0.4, height=0.6)],
            max_instances=10,
        ),
    )

    # The fake provider supports at most 3 instances.
    prompt = spy_segment.call_args.kwargs["prompt"]
    assert prompt.max_masks == 3
    assert prompt.text is None
    assert prompt.points == []
    assert [(box.x_min, box.y_min, box.x_max, box.y_max) for box in prompt.boxes] == [
        (10, 10, 50, 40)
    ]
    assert [prediction.bbox for prediction in response.predictions] == [
        AnnotationPreviewBox(x=10, y=10, width=41, height=31)
    ]


def test_create_instances_preview__blank_text_without_boxes() -> None:
    with pytest.raises(ValidationError):
        InstancesAnnotationRequest(collection_id=uuid4(), sample_id=uuid4(), prompt="   ")


def _image(width: int, height: int) -> ProviderImage:
    return ProviderImage(
        sample_id=uuid4(), width=width, height=height, file_name="img.png", read_bytes=lambda: b""
    )


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
