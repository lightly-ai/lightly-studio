from __future__ import annotations

import logging
from uuid import uuid4

import pytest
from pytest_mock import MockerFixture

from lightly_studio.assisted_labeling.fake_provider import FakeProvider
from lightly_studio.assisted_labeling.provider import (
    PointPrompt,
    ProviderError,
    ProviderImage,
    SegmentationPrompt,
)
from lightly_studio.services.assisted_labeling_service import run_provider

PROMPT = SegmentationPrompt(
    points=[PointPrompt(x=50, y=25, positive=True)], boxes=[], text=None, max_masks=1
)


def test_segment(caplog: pytest.LogCaptureFixture, mocker: MockerFixture) -> None:
    provider = FakeProvider()
    spy_segment = mocker.spy(provider, "segment")
    image = _image()

    with caplog.at_level(logging.DEBUG, logger=run_provider.__name__):
        predictions = run_provider.segment(provider=provider, image=image, prompt=PROMPT)

    assert len(predictions) == 1
    assert predictions[0].score == 0.9
    spy_segment.assert_called_once_with(image=image, prompt=PROMPT)
    assert f"Provider 'fake' segmented sample {image.sample_id} in" in caplog.text


def test_segment__provider_error(mocker: MockerFixture) -> None:
    provider = FakeProvider()
    mocker.patch.object(provider, "segment", side_effect=ProviderError("Request timed out."))

    with pytest.raises(ProviderError, match=r"Request timed out\."):
        run_provider.segment(provider=provider, image=_image(), prompt=PROMPT)


def _image() -> ProviderImage:
    return ProviderImage(
        sample_id=uuid4(), width=100, height=50, file_name="img.png", read_bytes=lambda: b""
    )
