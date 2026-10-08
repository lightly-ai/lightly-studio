from __future__ import annotations

from lightly_studio.assisted_labeling.provider import BoxPrompt, PointPrompt
from lightly_studio.models.assisted_labeling import AnnotationBox, AnnotationPoint
from lightly_studio.services.assisted_labeling_service import convert_prompts


def test_to_point_prompt() -> None:
    point = AnnotationPoint(x=0.255, y=0.5, positive=False)

    prompt = convert_prompts.to_point_prompt(point=point, width=100, height=50)

    assert prompt == PointPrompt(x=25, y=25, positive=False)


def test_to_point_prompt__clamps_to_last_pixel() -> None:
    point = AnnotationPoint(x=1.0, y=1.0, positive=True)

    prompt = convert_prompts.to_point_prompt(point=point, width=100, height=50)

    assert prompt == PointPrompt(x=99, y=49, positive=True)


def test_to_box_prompt() -> None:
    box = AnnotationBox(x=0.105, y=0.2, width=0.4, height=0.61)

    prompt = convert_prompts.to_box_prompt(box=box, width=100, height=50)

    assert prompt == BoxPrompt(x_min=10, y_min=10, x_max=51, y_max=41)


def test_to_box_prompt__clamps_to_image() -> None:
    box = AnnotationBox(x=0.5, y=0.5, width=0.5000001, height=0.5000001)

    prompt = convert_prompts.to_box_prompt(box=box, width=100, height=50)

    assert prompt == BoxPrompt(x_min=50, y_min=25, x_max=100, y_max=50)
