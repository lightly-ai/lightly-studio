from __future__ import annotations

import io
import json
from typing import Any, cast

import numpy as np
import pytest
import requests
from PIL import Image

from lightly_studio.assisted_labeling import openai_astra_provider
from lightly_studio.assisted_labeling.openai_astra_provider import (
    EncodedImage,
    ImageScale,
    OpenAIAstraProvider,
)
from lightly_studio.assisted_labeling.provider import (
    BoxPrompt,
    OutputType,
    PointPrompt,
    ProviderError,
    ProviderImage,
)
from tests.assisted_labeling.helpers import FakeResponse, FakeSession, make_image, make_prompt

RESPONSES_URL = "https://api.openai.com/v1/responses"


def _png_bytes(width: int, height: int) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height)).save(buffer, format="PNG")
    return buffer.getvalue()


def _completed_output(instances: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "completed",
        "output": [
            {"type": "reasoning", "summary": []},
            {
                "type": "message",
                "content": [{"type": "output_text", "text": json.dumps({"instances": instances})}],
            },
        ],
    }


def _make_provider(output: dict[str, Any]) -> tuple[OpenAIAstraProvider, FakeSession]:
    session = FakeSession(responses={("POST", RESPONSES_URL): [FakeResponse(json_body=output)]})
    return OpenAIAstraProvider(session=cast(requests.Session, session)), session


class TestOpenAIAstraProvider:
    def test_is_available(self, monkeypatch: pytest.MonkeyPatch) -> None:
        provider, _ = _make_provider(output={})

        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        assert provider.is_available() == "Set the OPENAI_API_KEY environment variable."
        monkeypatch.setenv("OPENAI_API_KEY", "secret")
        assert provider.is_available() is None

    def test_segment__polygons(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "secret")
        provider, session = _make_provider(
            output=_completed_output(
                instances=[{"polygons": [[10, 10, 29, 10, 29, 19, 10, 19]], "confidence": 0.8}]
            )
        )
        image = make_image(width=100, height=50, data=_png_bytes(width=100, height=50))

        predictions = provider.segment(image=image, prompt=make_prompt(text="dog", max_masks=4))

        assert len(predictions) == 1
        rows, columns = np.nonzero(predictions[0].mask)
        assert (columns.min(), columns.max(), rows.min(), rows.max()) == (10, 29, 10, 19)
        assert predictions[0].score == 0.8
        assert predictions[0].class_name == "dog"
        call = session.calls[0]
        assert call["headers"] == {"Authorization": "Bearer secret"}
        assert call["json"]["model"] == "gpt-6-astra"
        image_content = call["json"]["input"][0]["content"][1]
        assert image_content["detail"] == "original"
        assert image_content["image_url"].startswith("data:image/jpeg;base64,")

    def test_segment__boxes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "secret")
        provider, session = _make_provider(
            output=_completed_output(
                instances=[{"x_min": 5, "y_min": 6, "x_max": 15, "y_max": 16, "confidence": 0.7}]
            )
        )
        image = make_image(width=100, height=50, data=_png_bytes(width=100, height=50))

        predictions = provider.segment(
            image=image,
            prompt=make_prompt(
                points=[PointPrompt(x=10, y=10, positive=True)], output_type=OutputType.BOX
            ),
        )

        assert len(predictions) == 1
        assert predictions[0].mask.sum() == 10 * 10
        assert predictions[0].mask[6:16, 5:15].all()
        schema = session.calls[0]["json"]["text"]["format"]["schema"]
        assert "x_min" in schema["properties"]["instances"]["items"]["properties"]

    def test_segment__without_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        provider, _ = _make_provider(output={})

        with pytest.raises(ProviderError, match="OPENAI_API_KEY"):
            provider.segment(image=make_image(width=10, height=10), prompt=make_prompt())

    def test_segment__http_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "secret")
        session = FakeSession(
            responses={("POST", RESPONSES_URL): [FakeResponse(json_body="bad", status_code=400)]}
        )
        provider = OpenAIAstraProvider(session=cast(requests.Session, session))
        image = make_image(width=10, height=10, data=_png_bytes(width=10, height=10))

        with pytest.raises(ProviderError, match="status 400"):
            provider.segment(image=image, prompt=make_prompt(text="dog"))

    def test_prepare__caches_encoded_image(self) -> None:
        provider, _ = _make_provider(output={})
        read_count = 0

        def read_bytes() -> bytes:
            nonlocal read_count
            read_count += 1
            return _png_bytes(width=10, height=10)

        image = ProviderImage(
            sample_id=make_image(width=10, height=10).sample_id,
            width=10,
            height=10,
            file_name="image.png",
            read_bytes=read_bytes,
        )

        provider.prepare(image=image)
        provider.prepare(image=image)

        assert read_count == 1


def test_encode_image__downscales_longest_side() -> None:
    encoded = openai_astra_provider.encode_image(
        data=_png_bytes(width=400, height=100), max_side=200
    )

    assert (encoded.width, encoded.height) == (200, 50)
    assert encoded.data_uri.startswith("data:image/jpeg;base64,")


def test_encode_image__invalid() -> None:
    with pytest.raises(ProviderError, match="could not be decoded"):
        openai_astra_provider.encode_image(data=b"not an image", max_side=200)


def test_scale_prompt() -> None:
    prompt = openai_astra_provider.scale_prompt(
        prompt=make_prompt(
            points=[PointPrompt(x=100, y=50, positive=False)],
            boxes=[BoxPrompt(x_min=10, y_min=20, x_max=30, y_max=40)],
        ),
        scale=ImageScale(width=200, height=200, scale_x=0.5, scale_y=0.25),
    )

    assert prompt.points == [PointPrompt(x=50, y=12, positive=False)]
    assert prompt.boxes == [BoxPrompt(x_min=5, y_min=5, x_max=15, y_max=10)]


def test_build_request_body() -> None:
    body = openai_astra_provider.build_request_body(
        image=EncodedImage(data_uri="data:image/jpeg;base64,AA==", width=200, height=100),
        prompt=make_prompt(text="dog", max_masks=4),
        reasoning_effort="high",
    )

    assert body["reasoning"] == {"effort": "high"}
    assert body["text"]["format"]["type"] == "json_schema"
    text_content = body["input"][0]["content"][0]
    assert "The image is 200 px wide and 100 px tall." in text_content["text"]


def test_extract_output_text__incomplete() -> None:
    with pytest.raises(ProviderError, match="status 'incomplete'"):
        openai_astra_provider.extract_output_text(
            output={"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}}
        )


def test_extract_output_text__refusal() -> None:
    output = {
        "status": "completed",
        "output": [{"type": "message", "content": [{"type": "refusal", "refusal": "No."}]}],
    }

    with pytest.raises(ProviderError, match="refused the request: No"):
        openai_astra_provider.extract_output_text(output=output)


def test_extract_output_text__no_message() -> None:
    with pytest.raises(ProviderError, match="no output text"):
        openai_astra_provider.extract_output_text(output={"status": "completed", "output": []})


def test_parse_instances__scales_and_skips_empty_masks() -> None:
    text = json.dumps(
        {
            "instances": [
                {"polygons": [[5, 5, 14, 5, 14, 9, 5, 9]], "confidence": 0.9},
                {"polygons": [[1, 1]], "confidence": 0.5},
            ]
        }
    )

    predictions = openai_astra_provider.parse_instances(
        text=text,
        output_type=OutputType.MASK,
        scale=ImageScale(width=40, height=20, scale_x=0.5, scale_y=0.5),
        class_name=None,
    )

    assert len(predictions) == 1
    rows, columns = np.nonzero(predictions[0].mask)
    assert (columns.min(), columns.max(), rows.min(), rows.max()) == (10, 28, 10, 18)


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        json.dumps({"other": []}),
        json.dumps({"instances": [{"polygons": [[1, 2, 3, 4, 5, 6]]}]}),
    ],
)
def test_parse_instances__invalid(text: str) -> None:
    with pytest.raises(ProviderError, match="invalid instance list"):
        openai_astra_provider.parse_instances(
            text=text,
            output_type=OutputType.MASK,
            scale=ImageScale(width=10, height=10, scale_x=1.0, scale_y=1.0),
            class_name=None,
        )


def test_polygons_to_mask__multiple_parts() -> None:
    mask = openai_astra_provider.polygons_to_mask(
        polygons=[[0, 0, 2, 0, 2, 2, 0, 2], [6, 6, 8, 6, 8, 8, 6, 8], [1, 2, 3]],
        scale=ImageScale(width=10, height=10, scale_x=1.0, scale_y=1.0),
    )

    assert mask.shape == (10, 10)
    assert mask.dtype == np.bool_
    assert mask[0:3, 0:3].all()
    assert mask[6:9, 6:9].all()
    assert mask.sum() == 2 * 3 * 3


def test_box_to_mask__clips_to_image() -> None:
    mask = openai_astra_provider.box_to_mask(box=[-5.0, 2.5, 4.2, 20.0], width=10, height=8)

    rows, columns = np.nonzero(mask)
    assert (columns.min(), columns.max(), rows.min(), rows.max()) == (0, 4, 2, 7)


def test_estimate_cost_usd() -> None:
    usage = {
        "input_tokens": 3000,
        "input_tokens_details": {"cached_tokens": 1000},
        "output_tokens": 4000,
        "output_tokens_details": {"reasoning_tokens": 1500},
    }

    # 2000 * $10 + 1000 * $1 + 4000 * $50 per million tokens.
    assert openai_astra_provider.estimate_cost_usd(usage=usage) == pytest.approx(0.221)


def test_estimate_cost_usd__empty() -> None:
    assert openai_astra_provider.estimate_cost_usd(usage={}) == 0.0
