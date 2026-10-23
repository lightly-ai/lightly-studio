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


def test_to_point_prompts() -> None:
    points = [
        AnnotationPoint(x=0.0, y=0.0, positive=True),
        AnnotationPoint(x=0.5, y=0.5, positive=False),
    ]

    assert convert_prompts.to_point_prompts(points=points, width=10, height=4) == [
        PointPrompt(x=0, y=0, positive=True),
        PointPrompt(x=5, y=2, positive=False),
    ]


def test_to_point_prompts__none() -> None:
    assert convert_prompts.to_point_prompts(points=None, width=10, height=4) == []


def test_to_box_prompt() -> None:
    box = AnnotationBox(x=0.105, y=0.2, width=0.4, height=0.61)

    prompt = convert_prompts.to_box_prompt(box=box, width=100, height=50)

    assert prompt == BoxPrompt(x_min=10, y_min=10, x_max=51, y_max=41)


def test_to_box_prompt__clamps_to_image() -> None:
    box = AnnotationBox(x=0.5, y=0.5, width=0.5000001, height=0.5000001)

    prompt = convert_prompts.to_box_prompt(box=box, width=100, height=50)

    assert prompt == BoxPrompt(x_min=50, y_min=25, x_max=100, y_max=50)


def test_to_box_prompt__at_least_one_pixel() -> None:
    # 0.5 + 1e-17 == 0.5 in float, so the box has no pixel before the minimum size.
    box = AnnotationBox(x=0.5, y=0.5, width=1e-17, height=1e-17)

    prompt = convert_prompts.to_box_prompt(box=box, width=100, height=50)

    assert prompt == BoxPrompt(x_min=50, y_min=25, x_max=51, y_max=26)


def test_to_box_prompt__edge() -> None:
    box = AnnotationBox(x=0.99, y=0.98, width=0.01, height=0.02)

    prompt = convert_prompts.to_box_prompt(box=box, width=100, height=50)

    assert prompt == BoxPrompt(x_min=99, y_min=49, x_max=100, y_max=50)


def test_to_box_prompts() -> None:
    boxes = [
        AnnotationBox(x=0.0, y=0.0, width=0.5, height=0.5),
        AnnotationBox(x=0.5, y=0.5, width=0.5, height=0.5),
    ]

    assert convert_prompts.to_box_prompts(boxes=boxes, width=10, height=4) == [
        BoxPrompt(x_min=0, y_min=0, x_max=5, y_max=2),
        BoxPrompt(x_min=5, y_min=2, x_max=10, y_max=4),
    ]


def test_to_box_prompts__none() -> None:
    assert convert_prompts.to_box_prompts(boxes=None, width=10, height=4) == []
