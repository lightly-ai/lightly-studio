from __future__ import annotations

import logging

import numpy as np
import pytest

from lightly_studio.assisted_labeling.provider import (
    PointPrompt,
    Prediction,
    ProviderError,
)
from lightly_studio.services.assisted_labeling_service import run_provider
from tests.assisted_labeling import helpers
from tests.services.assisted_labeling_service.helpers import StubProvider

PROMPT = helpers.make_prompt(points=[PointPrompt(x=50, y=25, positive=True)])


def test_segment(caplog: pytest.LogCaptureFixture) -> None:
    prediction = Prediction(mask=np.ones((50, 100), dtype=np.bool_), score=0.9)
    provider = StubProvider(predictions=[prediction])
    image = helpers.make_image(width=100, height=50)

    with caplog.at_level(logging.DEBUG, logger=run_provider.__name__):
        predictions = run_provider.segment(provider=provider, image=image, prompt=PROMPT)

    assert predictions == [prediction]
    assert provider.prompts == [PROMPT]
    assert f"Segmented sample {image.sample_id} in" in caplog.text


def test_segment__provider_error() -> None:
    provider = StubProvider(error=ProviderError("Request timed out."))

    with pytest.raises(ProviderError, match=r"Request timed out\."):
        run_provider.segment(
            provider=provider, image=helpers.make_image(width=100, height=50), prompt=PROMPT
        )
