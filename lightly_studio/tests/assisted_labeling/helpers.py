from __future__ import annotations

from uuid import UUID

from lightly_studio.assisted_labeling.provider import (
    BoxPrompt,
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
) -> SegmentationPrompt:
    return SegmentationPrompt(
        points=points or [],
        boxes=boxes or [],
        text=text,
        max_masks=max_masks,
    )
