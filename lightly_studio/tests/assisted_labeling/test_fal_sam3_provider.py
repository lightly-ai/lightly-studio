from __future__ import annotations

import threading
from typing import cast
from uuid import UUID

import numpy as np
import pytest
import requests

from lightly_studio.assisted_labeling import fal_http, fal_sam3_provider, fal_storage, registry
from lightly_studio.assisted_labeling.fal_sam3_provider import FalSam3Provider
from lightly_studio.assisted_labeling.provider import (
    BoxPrompt,
    PointPrompt,
    ProviderError,
    ProviderImage,
)
from tests.assisted_labeling.helpers import FakeResponse, FakeSession, make_image, make_prompt

SUBMIT_URL = "https://queue.fal.run/fal-ai/sam-3/image-rle"
STATUS_URL = "https://queue.fal.run/fal-ai/sam-3/requests/1/status"
RESPONSE_URL = "https://queue.fal.run/fal-ai/sam-3/requests/1"
CDN_UPLOAD_URL = "https://v3.fal.media/files/upload"
IMAGE_URL = "https://v3.fal.media/files/image.jpg"


def _make_session(rle_output: dict[str, object]) -> FakeSession:
    return FakeSession(
        responses={
            ("POST", fal_storage.CDN_TOKEN_URL): [
                FakeResponse(
                    json_body={
                        "token": "tok",
                        "token_type": "Bearer",
                        "base_url": "https://v3.fal.media",
                        "expires_at": "2999-01-01T00:00:00Z",
                    }
                )
            ],
            ("POST", CDN_UPLOAD_URL): [FakeResponse(json_body={"access_url": IMAGE_URL})],
            ("POST", SUBMIT_URL): [
                FakeResponse(
                    json_body={
                        "request_id": "1",
                        "status_url": STATUS_URL,
                        "response_url": RESPONSE_URL,
                    }
                )
            ],
            ("GET", STATUS_URL): [FakeResponse(json_body={"status": "COMPLETED"})],
            ("GET", RESPONSE_URL): [FakeResponse(json_body=rle_output)],
        }
    )


def _make_provider(session: FakeSession) -> FalSam3Provider:
    return FalSam3Provider(
        session=cast(requests.Session, session),
        polling=fal_http.PollingConfig(timeout_s=10.0, interval_s=0.0),
    )


class TestFalSam3Provider:
    def test_is_available(self, monkeypatch: pytest.MonkeyPatch) -> None:
        provider = _make_provider(session=FakeSession(responses={}))

        monkeypatch.delenv("FAL_KEY", raising=False)
        assert provider.is_available() == "Set the FAL_KEY environment variable."
        monkeypatch.setenv("FAL_KEY", "secret")
        assert provider.is_available() is None

    def test_capabilities(self) -> None:
        capabilities = _make_provider(session=FakeSession(responses={})).capabilities()

        assert capabilities.negative_points
        assert capabilities.text_prompt
        assert capabilities.max_instances == 32

    def test_segment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("FAL_KEY", "secret")
        session = _make_session(rle_output={"rle": "1 2", "scores": [0.75], "metadata": []})
        provider = _make_provider(session=session)
        image = make_image(width=4, height=2, sample_id=UUID(int=1))
        prompt = make_prompt(points=[PointPrompt(x=1, y=0, positive=True)])

        predictions = provider.segment(image=image, prompt=prompt)

        assert len(predictions) == 1
        np.testing.assert_array_equal(
            predictions[0].mask, np.array([[False, True, True, False], [False] * 4])
        )
        assert predictions[0].score == 0.75
        submit_call = session.calls_to(method="POST", url=SUBMIT_URL)[0]
        assert submit_call["json"]["image_url"] == IMAGE_URL
        assert submit_call["headers"] == {"Authorization": "Key secret"}

    def test_segment__uploads_once_per_sample(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("FAL_KEY", "secret")
        session = _make_session(rle_output={"rle": []})
        provider = _make_provider(session=session)
        image = make_image(width=4, height=2, sample_id=UUID(int=1))

        provider.segment(image=image, prompt=make_prompt(text="car", max_masks=5))
        provider.segment(image=image, prompt=make_prompt(text="car", max_masks=5))

        assert len(session.calls_to(method="POST", url=CDN_UPLOAD_URL)) == 1

    def test_segment__missing_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("FAL_KEY", raising=False)
        provider = _make_provider(session=FakeSession(responses={}))

        with pytest.raises(ProviderError, match="Set the FAL_KEY environment variable"):
            provider.segment(image=make_image(width=4, height=2), prompt=make_prompt(text="car"))

    def test_segment__upload_error_releases_lock(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("FAL_KEY", "secret")
        session = _make_session(rle_output={})
        session._responses[("POST", CDN_UPLOAD_URL)] = [FakeResponse(json_body={}, status_code=500)]
        provider = _make_provider(session=session)

        with pytest.raises(ProviderError):
            provider.segment(image=make_image(width=4, height=2), prompt=make_prompt(text="car"))

        assert provider._upload_locks == {}

    def test_segment__upload_error_from_image_data(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("FAL_KEY", "secret")
        provider = _make_provider(session=_make_session(rle_output={}))

        def read_bytes() -> bytes:
            raise ProviderError("unreadable")

        image = ProviderImage(
            sample_id=UUID(int=1), width=4, height=2, file_name="a.jpg", read_bytes=read_bytes
        )

        with pytest.raises(ProviderError, match="unreadable"):
            provider.segment(image=image, prompt=make_prompt(text="car"))

        assert provider._upload_locks == {}


def test_get_image_url__keeps_lock_of_other_call() -> None:
    provider = _make_provider(session=FakeSession(responses={}))
    image = make_image(width=4, height=2)
    other_lock = threading.Lock()

    def read_bytes() -> bytes:
        # Another call replaces the lock while this upload runs.
        provider._upload_locks[image.sample_id] = other_lock
        raise ProviderError("unreadable")

    failing = ProviderImage(
        sample_id=image.sample_id, width=4, height=2, file_name="a.jpg", read_bytes=read_bytes
    )

    with pytest.raises(ProviderError):
        provider._get_image_url(image=failing, fal_key="secret")

    assert provider._upload_locks == {image.sample_id: other_lock}


def test_registry__get_provider() -> None:
    provider = registry.get_provider("fal_sam3")

    assert isinstance(provider, FalSam3Provider)
    assert provider.provider_id == "fal_sam3"


class TestBuildRequestBody:
    def test_points(self) -> None:
        prompt = make_prompt(
            points=[PointPrompt(x=3, y=4, positive=True), PointPrompt(x=5, y=6, positive=False)]
        )

        body = fal_sam3_provider.build_request_body(image_url="url", prompt=prompt)

        assert body == {
            "image_url": "url",
            "prompt": "",
            "point_prompts": [
                {"x": 3, "y": 4, "label": 1, "object_id": 0},
                {"x": 5, "y": 6, "label": 0, "object_id": 0},
            ],
            "max_masks": 1,
            "return_multiple_masks": False,
            "include_scores": True,
            "include_boxes": False,
            "apply_mask": False,
        }

    def test_boxes(self) -> None:
        prompt = make_prompt(boxes=[BoxPrompt(x_min=1, y_min=2, x_max=3, y_max=4)])

        body = fal_sam3_provider.build_request_body(image_url="url", prompt=prompt)

        assert body["box_prompts"] == [{"x_min": 1, "y_min": 2, "x_max": 3, "y_max": 4}]
        assert "point_prompts" not in body
        assert body["prompt"] == ""

    def test_text(self) -> None:
        prompt = make_prompt(text="person", max_masks=10)

        body = fal_sam3_provider.build_request_body(image_url="url", prompt=prompt)

        assert body["prompt"] == "person"
        assert body["max_masks"] == 10
        assert body["return_multiple_masks"] is True
        assert "point_prompts" not in body
        assert "box_prompts" not in body

    @pytest.mark.parametrize(("max_masks", "expected"), [(0, 1), (100, 32)])
    def test_max_masks_clamped(self, max_masks: int, expected: int) -> None:
        prompt = make_prompt(text="person", max_masks=max_masks)

        body = fal_sam3_provider.build_request_body(image_url="url", prompt=prompt)

        assert body["max_masks"] == expected


class TestParseResponse:
    def test_list(self) -> None:
        output = {"rle": ["0 1", "", "7 1"], "scores": [0.5, 0.6, 0.7]}

        predictions = fal_sam3_provider.parse_response(output=output, width=4, height=2)

        assert len(predictions) == 2
        assert predictions[0].mask[0, 0]
        assert predictions[0].score == 0.5
        assert predictions[1].mask[1, 3]
        assert predictions[1].score == 0.7

    def test_without_scores(self) -> None:
        predictions = fal_sam3_provider.parse_response(output={"rle": "0 1"}, width=4, height=2)

        assert len(predictions) == 1
        assert predictions[0].score is None
        assert predictions[0].class_name is None

    def test_invalid_score(self) -> None:
        with pytest.raises(ProviderError, match="invalid score"):
            fal_sam3_provider.parse_response(
                output={"rle": "0 1", "scores": ["high"]}, width=4, height=2
            )

    @pytest.mark.parametrize("output", [{}, {"rle": None}, {"rle": ""}, {"rle": []}])
    def test_empty(self, output: dict[str, object]) -> None:
        assert fal_sam3_provider.parse_response(output=output, width=4, height=2) == []


def test_decode_rle() -> None:
    mask = fal_sam3_provider.decode_rle(rle="1 2 5 3", width=4, height=2)

    expected = np.array([[False, True, True, False], [False, True, True, True]])
    np.testing.assert_array_equal(mask, expected)
    assert mask.dtype == np.bool_


def test_decode_rle__start_offset() -> None:
    mask = fal_sam3_provider.decode_rle(rle="1 2", width=4, height=2, start_offset=1)

    np.testing.assert_array_equal(mask, np.array([[True, True, False, False], [False] * 4]))


def test_decode_rle__golden() -> None:
    # 4x3 mask, row-major "start length" runs: row 0 pixels 1-2, row 1 pixel 3, row 2 pixel 0.
    mask = fal_sam3_provider.decode_rle(rle="1 2 7 1 8 1", width=4, height=3)

    expected = np.array(
        [
            [False, True, True, False],
            [False, False, False, True],
            [True, False, False, False],
        ]
    )
    np.testing.assert_array_equal(mask, expected)


def test_decode_rle__empty() -> None:
    mask = fal_sam3_provider.decode_rle(rle="", width=4, height=2)

    assert mask.shape == (2, 4)
    assert not mask.any()


def test_decode_rle__clips_run() -> None:
    mask = fal_sam3_provider.decode_rle(rle="6 5", width=4, height=2)

    np.testing.assert_array_equal(mask, np.array([[False] * 4, [False, False, True, True]]))


@pytest.mark.parametrize("rle", ["1 2 3", "1 a"])
def test_decode_rle__invalid(rle: str) -> None:
    with pytest.raises(ProviderError):
        fal_sam3_provider.decode_rle(rle=rle, width=4, height=2)
