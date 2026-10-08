from __future__ import annotations

from typing import Any
from uuid import UUID

from lightly_studio.assisted_labeling.provider import (
    BoxPrompt,
    OutputType,
    PointPrompt,
    ProviderImage,
    SegmentationPrompt,
)

DEFAULT_SAMPLE_ID = UUID(int=1)


def make_image(
    width: int,
    height: int,
    sample_id: UUID = DEFAULT_SAMPLE_ID,
    file_name: str = "image.jpg",
    data: bytes = b"image-bytes",
) -> ProviderImage:
    return ProviderImage(
        sample_id=sample_id,
        width=width,
        height=height,
        file_name=file_name,
        read_bytes=lambda: data,
    )


def make_prompt(
    points: list[PointPrompt] | None = None,
    boxes: list[BoxPrompt] | None = None,
    text: str | None = None,
    max_masks: int = 1,
    output_type: OutputType = OutputType.MASK,
) -> SegmentationPrompt:
    return SegmentationPrompt(
        points=points or [],
        boxes=boxes or [],
        text=text,
        max_masks=max_masks,
        output_type=output_type,
    )


class FakeResponse:
    """Minimal stand-in for `requests.Response`."""

    def __init__(self, json_body: object = None, status_code: int = 200) -> None:
        self._json_body = json_body
        self.status_code = status_code
        self.ok = status_code < 400
        self.text = str(json_body)

    def json(self) -> object:
        return self._json_body


class FakeSession:
    """Records requests and answers them with queued responses per (method, url)."""

    def __init__(self, responses: dict[tuple[str, str], list[FakeResponse]]) -> None:
        self._responses = responses
        self.calls: list[dict[str, Any]] = []

    def request(self, **kwargs: Any) -> FakeResponse:
        self.calls.append(kwargs)
        queue = self._responses[(kwargs["method"], kwargs["url"])]
        return queue.pop(0) if len(queue) > 1 else queue[0]

    def calls_to(self, method: str, url: str) -> list[dict[str, Any]]:
        return [call for call in self.calls if (call["method"], call["url"]) == (method, url)]
