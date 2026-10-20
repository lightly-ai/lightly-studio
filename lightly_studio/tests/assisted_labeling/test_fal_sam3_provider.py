from __future__ import annotations

import importlib.util
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, cast
from uuid import UUID

import httpx
import numpy as np
import pytest
from fal_client import FalClientHTTPError, FalClientTimeoutError, SyncClient
from pytest_mock import MockerFixture

from lightly_studio.assisted_labeling import fal_sam3_provider
from lightly_studio.assisted_labeling.fal_sam3_provider import FalSam3Provider
from lightly_studio.assisted_labeling.provider import (
    BoxPrompt,
    PointPrompt,
    ProviderError,
    ProviderImage,
    ProviderUnavailableError,
)
from tests.assisted_labeling import helpers

IMAGE_URL = "https://v3.fal.media/files/image.jpg"


class FakeFalClient:
    """Records the calls of the provider and answers like `fal_client.SyncClient`."""

    def __init__(
        self,
        output: object = None,
        upload_error: Exception | None = None,
        run_error: Exception | None = None,
    ) -> None:
        self._output = output
        self._upload_error = upload_error
        self._run_error = run_error
        self.keys: list[str] = []
        self.uploads: list[dict[str, Any]] = []
        self.runs: list[dict[str, Any]] = []

    def create(self, fal_key: str) -> SyncClient:
        self.keys.append(fal_key)
        return cast(SyncClient, self)

    def upload(
        self,
        data: bytes,
        content_type: str,
        file_name: str | None = None,
        fallback_repository: list[str] | None = None,
    ) -> str:
        self.uploads.append(
            {
                "data": data,
                "content_type": content_type,
                "file_name": file_name,
                "fallback_repository": fallback_repository,
            }
        )
        if self._upload_error is not None:
            raise self._upload_error
        return IMAGE_URL

    def run(
        self,
        application: str,
        arguments: dict[str, Any],
        timeout: float | None = None,
        start_timeout: float | None = None,
    ) -> object:
        self.runs.append(
            {
                "application": application,
                "arguments": arguments,
                "timeout": timeout,
                "start_timeout": start_timeout,
            }
        )
        if self._run_error is not None:
            raise self._run_error
        return self._output


class BlockingUploadFalClient(FakeFalClient):
    """Blocks each upload until `release_upload` is set."""

    def __init__(self, output: object = None) -> None:
        super().__init__(output=output)
        self.upload_started = threading.Event()
        self.release_upload = threading.Event()

    def upload(
        self,
        data: bytes,
        content_type: str,
        file_name: str | None = None,
        fallback_repository: list[str] | None = None,
    ) -> str:
        self.upload_started.set()
        self.release_upload.wait(timeout=5)
        return super().upload(
            data=data,
            content_type=content_type,
            file_name=file_name,
            fallback_repository=fallback_repository,
        )


def _make_provider(mocker: MockerFixture, client: FakeFalClient) -> FalSam3Provider:
    mocker.patch.object(fal_sam3_provider, "_create_client", side_effect=client.create)
    return FalSam3Provider()


class TestFalSam3Provider:
    def test_unavailable_reason(
        self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(importlib.util, "find_spec", return_value=mocker.sentinel.spec)
        provider = _make_provider(mocker=mocker, client=FakeFalClient())

        monkeypatch.delenv("FAL_KEY", raising=False)
        assert provider.unavailable_reason() == "Set the FAL_KEY environment variable."
        monkeypatch.setenv("FAL_KEY", "secret")
        assert provider.unavailable_reason() is None

    def test_unavailable_reason__without_extra(
        self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        monkeypatch.setenv("FAL_KEY", "secret")
        mocker.patch.object(importlib.util, "find_spec", return_value=None)
        provider = _make_provider(mocker=mocker, client=FakeFalClient())

        assert (
            provider.unavailable_reason()
            == 'Install the fal extra: pip install "lightly-studio[fal]".'
        )

    def test_segment(self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
        monkeypatch.setenv("FAL_KEY", "secret")
        client = FakeFalClient(output={"rle": "2 2", "scores": [0.75], "metadata": []})
        provider = _make_provider(mocker=mocker, client=client)
        image = helpers.make_image(width=4, height=2, file_name="a.png", data=b"png-bytes")
        prompt = helpers.make_prompt(points=[PointPrompt(x=1, y=0, positive=True)])

        predictions = provider.segment(image=image, prompt=prompt)

        assert len(predictions) == 1
        np.testing.assert_array_equal(
            predictions[0].mask, np.array([[False, True, True, False], [False] * 4])
        )
        assert predictions[0].score == 0.75
        assert client.keys == ["secret"]
        assert client.uploads == [
            {
                "data": b"png-bytes",
                "content_type": "image/png",
                "file_name": "a.png",
                "fallback_repository": [],
            }
        ]
        assert len(client.runs) == 1
        assert client.runs[0]["application"] == "fal-ai/sam-3/image-rle"
        assert client.runs[0]["arguments"]["image_url"] == IMAGE_URL
        assert client.runs[0]["timeout"] == 60.0
        assert client.runs[0]["start_timeout"] == 60.0

    def test_segment__uploads_once_per_sample(
        self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        monkeypatch.setenv("FAL_KEY", "secret")
        client = FakeFalClient(output={"rle": []})
        provider = _make_provider(mocker=mocker, client=client)
        image = helpers.make_image(width=4, height=2, sample_id=UUID(int=1))

        provider.segment(image=image, prompt=helpers.make_prompt(text="car", max_masks=5))
        provider.segment(image=image, prompt=helpers.make_prompt(text="car", max_masks=5))

        assert len(client.uploads) == 1
        assert len(client.runs) == 2
        assert client.keys == ["secret"]

    def test_segment__cached_sample_does_not_wait_for_upload(
        self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        monkeypatch.setenv("FAL_KEY", "secret")
        client = BlockingUploadFalClient(output={"rle": []})
        provider = _make_provider(mocker=mocker, client=client)
        cached_image = helpers.make_image(width=4, height=2, sample_id=UUID(int=1))
        new_image = helpers.make_image(width=4, height=2, sample_id=UUID(int=2))
        prompt = helpers.make_prompt(text="car")
        client.release_upload.set()
        provider.segment(image=cached_image, prompt=prompt)
        client.release_upload.clear()

        with ThreadPoolExecutor(max_workers=2) as executor:
            new_future = executor.submit(provider.segment, image=new_image, prompt=prompt)
            assert client.upload_started.wait(timeout=5)
            cached_future = executor.submit(provider.segment, image=cached_image, prompt=prompt)
            assert cached_future.result(timeout=5) == []
            assert not new_future.done()
            client.release_upload.set()
            assert new_future.result(timeout=5) == []

        assert len(client.uploads) == 2

    def test_segment__uploads_again_after_http_error(
        self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        monkeypatch.setenv("FAL_KEY", "secret")
        error = FalClientHTTPError(
            message="File not found",
            status_code=422,
            response_headers={},
            response=httpx.Response(status_code=422),
        )
        client = FakeFalClient(run_error=error)
        provider = _make_provider(mocker=mocker, client=client)
        image = helpers.make_image(width=4, height=2)

        for _ in range(2):
            with pytest.raises(ProviderError, match=r"^fal\.ai request failed with status 422\.$"):
                provider.segment(image=image, prompt=helpers.make_prompt(text="car"))

        assert len(client.uploads) == 2

    def test_segment__keeps_image_url_after_timeout(
        self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        monkeypatch.setenv("FAL_KEY", "secret")
        client = FakeFalClient(run_error=httpx.ReadTimeout("timed out"))
        provider = _make_provider(mocker=mocker, client=client)
        image = helpers.make_image(width=4, height=2)

        for _ in range(2):
            with pytest.raises(ProviderError, match="did not answer"):
                provider.segment(image=image, prompt=helpers.make_prompt(text="car"))

        assert len(client.uploads) == 1

    def test_segment__missing_key(
        self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        monkeypatch.delenv("FAL_KEY", raising=False)
        client = FakeFalClient()
        provider = _make_provider(mocker=mocker, client=client)

        with pytest.raises(ProviderUnavailableError, match="Set the FAL_KEY environment variable"):
            provider.segment(
                image=helpers.make_image(width=4, height=2), prompt=helpers.make_prompt(text="car")
            )

        assert client.keys == []

    def test_segment__missing_extra(
        self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        monkeypatch.setenv("FAL_KEY", "secret")
        mocker.patch.object(importlib.util, "find_spec", return_value=None)
        client = FakeFalClient()
        provider = _make_provider(mocker=mocker, client=client)

        with pytest.raises(ProviderUnavailableError, match="Install the fal extra"):
            provider.segment(
                image=helpers.make_image(width=4, height=2), prompt=helpers.make_prompt(text="car")
            )

        assert client.keys == []

    def test_segment__broken_extra(
        self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        monkeypatch.setenv("FAL_KEY", "secret")
        mocker.patch.object(fal_sam3_provider, "_create_client", side_effect=ImportError("broken"))
        provider = FalSam3Provider()

        with pytest.raises(ProviderUnavailableError, match="Install the fal extra"):
            provider.segment(
                image=helpers.make_image(width=4, height=2), prompt=helpers.make_prompt(text="car")
            )

    def test_segment__upload_error(
        self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        monkeypatch.setenv("FAL_KEY", "secret")
        client = FakeFalClient(upload_error=httpx.ConnectError("refused"))
        provider = _make_provider(mocker=mocker, client=client)
        image = helpers.make_image(width=4, height=2)

        with pytest.raises(ProviderError, match=r"^fal\.ai request failed\.$"):
            provider.segment(image=image, prompt=helpers.make_prompt(text="car"))
        with pytest.raises(ProviderError, match=r"^fal\.ai request failed\.$"):
            provider.segment(image=image, prompt=helpers.make_prompt(text="car"))

        assert len(client.uploads) == 2
        assert client.runs == []

    def test_segment__upload_error_from_image_data(
        self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        monkeypatch.setenv("FAL_KEY", "secret")
        provider = _make_provider(mocker=mocker, client=FakeFalClient())

        def read_bytes() -> bytes:
            raise ProviderError("unreadable")

        image = ProviderImage(
            sample_id=UUID(int=1), width=4, height=2, file_name="a.jpg", read_bytes=read_bytes
        )

        with pytest.raises(ProviderError, match="unreadable"):
            provider.segment(image=image, prompt=helpers.make_prompt(text="car"))

    @pytest.mark.parametrize(
        "error",
        [httpx.ReadTimeout("timed out"), FalClientTimeoutError(timeout=60.0)],
    )
    def test_segment__timeout(
        self, error: Exception, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        monkeypatch.setenv("FAL_KEY", "secret")
        provider = _make_provider(mocker=mocker, client=FakeFalClient(run_error=error))

        with pytest.raises(ProviderError, match=r"^fal\.ai did not answer within 60 s\.$"):
            provider.segment(
                image=helpers.make_image(width=4, height=2), prompt=helpers.make_prompt(text="car")
            )

    def test_segment__http_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
        mocker: MockerFixture,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        monkeypatch.setenv("FAL_KEY", "secret")
        error = FalClientHTTPError(
            message="Invalid image",
            status_code=422,
            response_headers={},
            response=httpx.Response(status_code=422),
        )
        provider = _make_provider(mocker=mocker, client=FakeFalClient(run_error=error))

        with pytest.raises(ProviderError, match=r"^fal\.ai request failed with status 422\.$"):
            provider.segment(
                image=helpers.make_image(width=4, height=2), prompt=helpers.make_prompt(text="car")
            )

        assert "Invalid image" in caplog.text

    def test_segment__start_timeout_expiry(
        self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        monkeypatch.setenv("FAL_KEY", "secret")
        response = httpx.Response(status_code=504, headers={"X-Fal-Request-Timeout-Type": "user"})
        error = FalClientHTTPError(
            message="Timed out",
            status_code=504,
            response_headers=dict(response.headers),
            response=response,
        )
        provider = _make_provider(mocker=mocker, client=FakeFalClient(run_error=error))

        with pytest.raises(ProviderError, match=r"^fal\.ai did not answer within 60 s\.$"):
            provider.segment(
                image=helpers.make_image(width=4, height=2), prompt=helpers.make_prompt(text="car")
            )

    def test_segment__invalid_json(
        self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        monkeypatch.setenv("FAL_KEY", "secret")
        error = json.JSONDecodeError(msg="Expecting value", doc="<html>", pos=0)
        provider = _make_provider(mocker=mocker, client=FakeFalClient(run_error=error))

        with pytest.raises(ProviderError, match="invalid response"):
            provider.segment(
                image=helpers.make_image(width=4, height=2), prompt=helpers.make_prompt(text="car")
            )

    def test_segment__upload_without_url(
        self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        monkeypatch.setenv("FAL_KEY", "secret")
        provider = _make_provider(
            mocker=mocker, client=FakeFalClient(upload_error=KeyError("access_url"))
        )

        with pytest.raises(ProviderError, match="invalid response"):
            provider.segment(
                image=helpers.make_image(width=4, height=2), prompt=helpers.make_prompt(text="car")
            )

    def test_segment__unexpected_output(
        self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        monkeypatch.setenv("FAL_KEY", "secret")
        provider = _make_provider(mocker=mocker, client=FakeFalClient(output=["0 1"]))

        with pytest.raises(ProviderError, match="unexpected JSON"):
            provider.segment(
                image=helpers.make_image(width=4, height=2), prompt=helpers.make_prompt(text="car")
            )


class TestBuildRequestBody:
    def test_points(self) -> None:
        prompt = helpers.make_prompt(
            points=[PointPrompt(x=3, y=4, positive=True), PointPrompt(x=5, y=6, positive=False)],
            text=None,
            max_masks=1,
        )

        body = fal_sam3_provider.build_request_body(image_url="url", prompt=prompt)

        assert body == {
            "image_url": "url",
            "prompt": "",
            "point_prompts": [
                {"x": 3, "y": 4, "label": 1, "object_id": 1},
                {"x": 5, "y": 6, "label": 0, "object_id": 1},
            ],
            "max_masks": 1,
            "return_multiple_masks": False,
            "include_scores": True,
            "include_boxes": False,
            "apply_mask": False,
        }

    def test_boxes(self) -> None:
        prompt = helpers.make_prompt(
            boxes=[BoxPrompt(x_min=1, y_min=2, x_max=3, y_max=4)], text=None, max_masks=1
        )

        body = fal_sam3_provider.build_request_body(image_url="url", prompt=prompt)

        assert body["box_prompts"] == [
            {"x_min": 1, "y_min": 2, "x_max": 3, "y_max": 4, "object_id": 1}
        ]
        assert "point_prompts" not in body
        assert body["prompt"] == ""

    def test_boxes__multiple_masks(self) -> None:
        prompt = helpers.make_prompt(
            boxes=[
                BoxPrompt(x_min=1, y_min=2, x_max=3, y_max=4),
                BoxPrompt(x_min=5, y_min=6, x_max=7, y_max=8),
            ],
            text=None,
            max_masks=10,
        )

        body = fal_sam3_provider.build_request_body(image_url="url", prompt=prompt)

        assert body["box_prompts"] == [
            {"x_min": 1, "y_min": 2, "x_max": 3, "y_max": 4},
            {"x_min": 5, "y_min": 6, "x_max": 7, "y_max": 8},
        ]

    def test_text(self) -> None:
        prompt = helpers.make_prompt(text="person", max_masks=10)

        body = fal_sam3_provider.build_request_body(image_url="url", prompt=prompt)

        assert body["prompt"] == "person"
        assert body["max_masks"] == 10
        assert body["return_multiple_masks"] is True
        assert "point_prompts" not in body
        assert "box_prompts" not in body


class TestParseResponse:
    def test_list(self) -> None:
        output = {"rle": ["1 1", "", "8 1"], "scores": [0.5, 0.6, 0.7]}

        predictions = fal_sam3_provider.parse_response(output=output, width=4, height=2)

        assert len(predictions) == 2
        assert predictions[0].mask[0, 0]
        assert predictions[0].score == 0.5
        assert predictions[1].mask[1, 3]
        assert predictions[1].score == 0.7

    @pytest.mark.parametrize("output", [{"rle": "1 1"}, {"rle": "1 1", "scores": None}])
    def test_without_scores(self, output: dict[str, object]) -> None:
        predictions = fal_sam3_provider.parse_response(output=output, width=4, height=2)

        assert len(predictions) == 1
        assert predictions[0].score is None

    def test_invalid_score(self) -> None:
        with pytest.raises(ProviderError, match="invalid score"):
            fal_sam3_provider.parse_response(
                output={"rle": "1 1", "scores": ["high"]}, width=4, height=2
            )

    @pytest.mark.parametrize("scores", [0.5, {"a": 1}, "9", 0, False, "", {}])
    def test_invalid_scores_type(self, scores: object) -> None:
        with pytest.raises(ProviderError, match="invalid scores"):
            fal_sam3_provider.parse_response(
                output={"rle": "1 1", "scores": scores}, width=4, height=2
            )

    @pytest.mark.parametrize("output", [{"rle": ""}, {"rle": []}])
    def test_empty(self, output: dict[str, object]) -> None:
        assert fal_sam3_provider.parse_response(output=output, width=4, height=2) == []

    @pytest.mark.parametrize("output", [{}, {"scores": [0.5]}])
    def test_missing_rle(self, output: dict[str, object]) -> None:
        with pytest.raises(ProviderError, match="no RLE"):
            fal_sam3_provider.parse_response(output=output, width=4, height=2)

    @pytest.mark.parametrize("rle", [None, 1, [1], ["0 1", None]])
    def test_invalid_rle_type(self, rle: object) -> None:
        with pytest.raises(ProviderError, match="invalid RLE"):
            fal_sam3_provider.parse_response(output={"rle": rle}, width=4, height=2)


def test_decode_rle() -> None:
    mask = fal_sam3_provider.decode_rle(rle="2 2 6 3", width=4, height=2)

    expected = np.array([[False, True, True, False], [False, True, True, True]])
    np.testing.assert_array_equal(mask, expected)
    assert mask.dtype == np.bool_


def test_decode_rle__fal_response() -> None:
    # First run of a fal.ai mask for a 160x96 image with a rectangle at x 20-69, y 10-39.
    mask = fal_sam3_provider.decode_rle(rle="1621 50", width=160, height=96)

    assert mask[10, 20:70].all()
    assert mask.sum() == 50


def test_decode_rle__empty() -> None:
    mask = fal_sam3_provider.decode_rle(rle="", width=4, height=2)

    assert mask.shape == (2, 4)
    assert not mask.any()


def test_decode_rle__clips_run() -> None:
    mask = fal_sam3_provider.decode_rle(rle="7 5", width=4, height=2)

    np.testing.assert_array_equal(mask, np.array([[False] * 4, [False, False, True, True]]))


@pytest.mark.parametrize("rle", ["1 2 3", "1 a", "0 -1", "-1 2"])
def test_decode_rle__invalid(rle: str) -> None:
    with pytest.raises(ProviderError):
        fal_sam3_provider.decode_rle(rle=rle, width=4, height=2)


@pytest.mark.parametrize(
    ("file_name", "expected"),
    [
        ("a.jpg", "image/jpeg"),
        ("a.JPEG", "image/jpeg"),
        ("a.png", "image/png"),
        ("a.webp", "image/webp"),
        ("a.gif", "image/gif"),
        ("a.bmp", "image/bmp"),
        ("a.TIF", "image/tiff"),
        ("a.tiff", "image/tiff"),
        ("a.heic", "image/jpeg"),
        ("a", "image/jpeg"),
    ],
)
def test_content_type_for(file_name: str, expected: str) -> None:
    assert fal_sam3_provider.content_type_for(file_name=file_name) == expected
