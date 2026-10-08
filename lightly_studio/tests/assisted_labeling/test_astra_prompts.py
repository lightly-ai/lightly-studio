from __future__ import annotations

from lightly_studio.assisted_labeling import astra_prompts
from lightly_studio.assisted_labeling.provider import BoxPrompt, OutputType, PointPrompt
from tests.assisted_labeling.helpers import make_prompt


def test_build_instructions__single_points() -> None:
    instructions = astra_prompts.build_instructions(
        prompt=make_prompt(
            points=[
                PointPrompt(x=10, y=20, positive=True),
                PointPrompt(x=30, y=40, positive=False),
            ],
            max_masks=1,
        ),
        width=200,
        height=100,
    )

    assert "The image is 200 px wide and 100 px tall." in instructions
    assert "Identify the single object" in instructions
    assert "Positive points lie on the object: (10, 20)." in instructions
    assert "Negative points lie outside the object: (30, 40)." in instructions
    assert "polygons" in instructions


def test_build_instructions__single_box() -> None:
    instructions = astra_prompts.build_instructions(
        prompt=make_prompt(boxes=[BoxPrompt(x_min=1, y_min=2, x_max=3, y_max=4)], max_masks=1),
        width=200,
        height=100,
    )

    assert "The object lies inside the boxes [x_min, y_min, x_max, y_max]: [1, 2, 3, 4]." in (
        instructions
    )
    assert "example instances" not in instructions


def test_build_instructions__instances_text_and_boxes() -> None:
    instructions = astra_prompts.build_instructions(
        prompt=make_prompt(
            text="dog", boxes=[BoxPrompt(x_min=1, y_min=2, x_max=3, y_max=4)], max_masks=8
        ),
        width=200,
        height=100,
    )

    assert "Find every object instance" in instructions
    assert "Return at most 8 instances" in instructions
    assert '- Each instance is a "dog".' in instructions
    assert "mark example instances: [1, 2, 3, 4]" in instructions
    assert "Identify the single object" not in instructions


def test_build_instructions__box_output() -> None:
    instructions = astra_prompts.build_instructions(
        prompt=make_prompt(text="dog", max_masks=8, output_type=OutputType.BOX),
        width=200,
        height=100,
    )

    assert "tightest axis-aligned bounding box" in instructions
    assert "polygons" not in instructions


def test_build_response_format__mask() -> None:
    response_format = astra_prompts.build_response_format(output_type=OutputType.MASK)

    assert response_format["strict"] is True
    instance = response_format["schema"]["properties"]["instances"]["items"]
    assert instance["required"] == ["polygons", "confidence"]
    assert instance["additionalProperties"] is False


def test_build_response_format__box() -> None:
    response_format = astra_prompts.build_response_format(output_type=OutputType.BOX)

    instance = response_format["schema"]["properties"]["instances"]["items"]
    assert instance["required"] == ["x_min", "y_min", "x_max", "y_max", "confidence"]
