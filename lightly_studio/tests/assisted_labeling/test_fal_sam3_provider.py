from __future__ import annotations

import dataclasses
from uuid import UUID

import pytest
from pytest_mock import MockerFixture

from lightly_studio.assisted_labeling import fal_http
from lightly_studio.assisted_labeling.fal_sam3_provider import FalSam3Provider
from lightly_studio.assisted_labeling.provider import (
    ProviderError,
    ProviderImage,
    ProviderNotCalledError,
    SegmentationPrompt,
)

IMAGE = ProviderImage(
    sample_id=UUID("00000000-0000-0000-0000-000000000002"),
    width=100,
    height=80,
    file_name="img.png",
    read_bytes=lambda: b"",
)
TEXT_PROMPT = SegmentationPrompt(points=[], boxes=[], text="cat", max_masks=1)


def test_segment__without_key_does_not_call_fal(
    mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("FAL_KEY", raising=False)
    run_queue_request = mocker.patch.object(fal_http, "run_queue_request")

    with pytest.raises(ProviderNotCalledError, match="FAL_KEY"):
        FalSam3Provider(session=mocker.MagicMock()).segment(image=IMAGE, prompt=TEXT_PROMPT)

    run_queue_request.assert_not_called()


def test_segment__unreadable_image_does_not_call_fal(
    mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAL_KEY", "k3y")
    run_queue_request = mocker.patch.object(fal_http, "run_queue_request")

    def _read_bytes() -> bytes:
        raise FileNotFoundError("missing image")

    image = dataclasses.replace(IMAGE, read_bytes=_read_bytes)

    with pytest.raises(ProviderNotCalledError, match="missing image"):
        FalSam3Provider(session=mocker.MagicMock()).segment(image=image, prompt=TEXT_PROMPT)

    run_queue_request.assert_not_called()


def test_segment__failed_upload_does_not_call_fal(
    mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAL_KEY", "k3y")
    mocker.patch.object(fal_http.FalUploader, "upload", side_effect=ProviderError("upload failed"))
    run_queue_request = mocker.patch.object(fal_http, "run_queue_request")

    with pytest.raises(ProviderNotCalledError, match="upload failed"):
        FalSam3Provider(session=mocker.MagicMock()).segment(image=IMAGE, prompt=TEXT_PROMPT)

    run_queue_request.assert_not_called()
