from __future__ import annotations

import time
from uuid import uuid4

from pytest_mock import MockerFixture

from lightly_studio.assisted_labeling.fake_provider import FakeProvider
from lightly_studio.assisted_labeling.provider import (
    PointPrompt,
    ProviderImage,
    SegmentationPrompt,
)
from lightly_studio.services.assisted_labeling_service import segment_timed


def test_segment_timed(mocker: MockerFixture) -> None:
    mocker.patch.object(time, "perf_counter", side_effect=[1.0, 1.25])
    image = ProviderImage(
        sample_id=uuid4(), width=100, height=50, file_name="img.png", read_bytes=lambda: b""
    )
    prompt = SegmentationPrompt(
        points=[PointPrompt(x=50, y=25, positive=True)], boxes=[], text=None, max_masks=1
    )

    predictions, latency_ms = segment_timed.segment_timed(
        provider=FakeProvider(), image=image, prompt=prompt
    )

    assert len(predictions) == 1
    assert latency_ms == 250.0
