"""Prompts and JSON schemas for segmentation with OpenAI GPT-6 Astra.

All coordinates are pixels of the image that is sent to the model.
"""

from __future__ import annotations

from typing import Any

from lightly_studio.assisted_labeling.provider import OutputType, PointPrompt, SegmentationPrompt

SCHEMA_NAME = "instances"

_COORDINATES = (
    "The image is {width} px wide and {height} px tall. Coordinates are pixels with (0, 0) "
    "at the top-left corner, x pointing right and y pointing down."
)
_SINGLE_TASK = (
    "Identify the single object that the hints below point to. Return exactly one instance "
    "for this object, or an empty list if no object matches the hints."
)
_INSTANCES_TASK = (
    "Find every object instance in the image that matches the hints below. Return one entry "
    "per instance and do not merge separate instances. Return at most {max_instances} "
    "instances, the most confident first, or an empty list if nothing matches."
)
_MASK_OUTPUT = (
    "For each instance, return one or more polygons that trace its visible outline as "
    "tightly as you can. Each polygon is a flat list [x1, y1, x2, y2, ...] with at least 3 "
    "vertices. Use as many vertices as the shape needs. Return more than one polygon only "
    "if occlusion splits the instance into separate parts. Also return a confidence in [0, 1]."
)
_BOX_OUTPUT = (
    "For each instance, return the tightest axis-aligned bounding box around its visible "
    "pixels as x_min, y_min, x_max, y_max, and a confidence in [0, 1]."
)


def build_instructions(prompt: SegmentationPrompt, width: int, height: int) -> str:
    """Returns the text prompt for the segmentation prompt.

    Args:
        prompt: Prompts in pixel coordinates of the sent image. `max_masks` of 1 selects
            the single-object mode, a larger value selects the all-instances mode.
        width: Width of the sent image in pixels.
        height: Height of the sent image in pixels.
    """
    single = prompt.max_masks == 1
    task = _SINGLE_TASK if single else _INSTANCES_TASK.format(max_instances=prompt.max_masks)
    output = _BOX_OUTPUT if prompt.output_type == OutputType.BOX else _MASK_OUTPUT
    sections = [
        _COORDINATES.format(width=width, height=height),
        task,
        "Hints:",
        *_hint_lines(prompt=prompt, single=single),
        output,
    ]
    return "\n\n".join(sections)


def build_response_format(output_type: OutputType) -> dict[str, Any]:
    """Returns the strict JSON schema format of the Responses API for the output type."""
    if output_type == OutputType.BOX:
        geometry: dict[str, Any] = {
            key: {"type": "number"} for key in ("x_min", "y_min", "x_max", "y_max")
        }
    else:
        geometry = {
            "polygons": {
                "type": "array",
                "items": {"type": "array", "items": {"type": "number"}},
            }
        }
    instance_properties = {**geometry, "confidence": {"type": "number"}}
    instance_schema = {
        "type": "object",
        "properties": instance_properties,
        "required": list(instance_properties),
        "additionalProperties": False,
    }
    return {
        "type": "json_schema",
        "name": SCHEMA_NAME,
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {"instances": {"type": "array", "items": instance_schema}},
            "required": ["instances"],
            "additionalProperties": False,
        },
    }


def _hint_lines(prompt: SegmentationPrompt, single: bool) -> list[str]:
    lines = []
    if prompt.text:
        noun = "The object is" if single else "Each instance is"
        lines.append(f'- {noun} a "{prompt.text}".')
    positives = [point for point in prompt.points if point.positive]
    negatives = [point for point in prompt.points if not point.positive]
    if positives:
        lines.append(f"- Positive points lie on the object: {_format_points(points=positives)}.")
    if negatives:
        lines.append(
            f"- Negative points lie outside the object: {_format_points(points=negatives)}."
        )
    if prompt.boxes:
        boxes = ", ".join(
            f"[{box.x_min}, {box.y_min}, {box.x_max}, {box.y_max}]" for box in prompt.boxes
        )
        if single:
            lines.append(
                f"- The object lies inside the boxes [x_min, y_min, x_max, y_max]: {boxes}. "
                "The boxes are approximate, cover the whole object."
            )
        else:
            lines.append(
                f"- The boxes [x_min, y_min, x_max, y_max] mark example instances: {boxes}. "
                "Find every object of the same kind, including the examples."
            )
    return lines


def _format_points(points: list[PointPrompt]) -> str:
    return ", ".join(f"({point.x}, {point.y})" for point in points)
