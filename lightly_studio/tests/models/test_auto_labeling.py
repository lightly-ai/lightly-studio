from uuid import UUID

import pytest
from pydantic import ValidationError

from lightly_studio.models.auto_labeling import (
    AnnotationDescriptor,
    InstancesAnnotationRequest,
    InteractiveAnnotationRequest,
)
from lightly_studio.services import auto_labeling


def _request(**conditioning: object) -> dict[str, object]:
    return {
        "collection_id": UUID("00000000-0000-0000-0000-000000000001"),
        "sample_id": UUID("00000000-0000-0000-0000-000000000002"),
        **conditioning,
    }


def _descriptor(*conditioning: str) -> AnnotationDescriptor:
    return AnnotationDescriptor(
        protocol_version="1.0",
        model_key="test-model",
        ready=True,
        capabilities=["segmentation_image_bytes"],
        supported_conditioning=list(conditioning),
        limits={"max_batch_size": 1, "max_request_bytes": 1_000_000},
    )


def test_interactive_request_accepts_a_normalized_box() -> None:
    request = InteractiveAnnotationRequest.model_validate(
        _request(boxes=[{"x": 0.1, "y": 0.2, "width": 0.4, "height": 0.3}])
    )

    assert request.boxes is not None
    assert request.boxes[0].width == 0.4


def test_interactive_request_rejects_multiple_conditioning_types() -> None:
    with pytest.raises(ValidationError, match="either points or boxes"):
        InteractiveAnnotationRequest.model_validate(
            _request(
                points=[{"x": 0.5, "y": 0.5, "positive": True}],
                boxes=[{"x": 0.1, "y": 0.2, "width": 0.4, "height": 0.3}],
            )
        )


def test_interactive_request_rejects_a_box_outside_the_image() -> None:
    with pytest.raises(ValidationError, match="conditioning box is invalid"):
        InteractiveAnnotationRequest.model_validate(
            _request(boxes=[{"x": 0.8, "y": 0.2, "width": 0.4, "height": 0.3}])
        )


def test_instances_request_accepts_prompt_and_boxes() -> None:
    request = InstancesAnnotationRequest.model_validate(
        _request(
            prompt="cars",
            boxes=[{"x": 0.1, "y": 0.2, "width": 0.4, "height": 0.3}],
        )
    )

    assert request.prompt == "cars"
    assert request.boxes is not None


def test_instances_request_requires_prompt_or_boxes() -> None:
    with pytest.raises(ValidationError, match="text prompt, boxes, or both"):
        InstancesAnnotationRequest.model_validate(_request())


def test_instances_request_rejects_a_blank_prompt_without_boxes() -> None:
    with pytest.raises(ValidationError, match="text prompt, boxes, or both"):
        InstancesAnnotationRequest.model_validate(_request(prompt=" "))


def test_instances_conditioning_uses_targets_for_a_text_prompt() -> None:
    request = InstancesAnnotationRequest.model_validate(_request(prompt="cars"))

    assert auto_labeling._build_instances_conditioning(
        request=request, descriptor=_descriptor("targets")
    ) == {"targets": [{"prompt": "cars", "class_name": "cars"}]}


def test_instances_conditioning_adds_center_points_for_box_only_requests() -> None:
    request = InstancesAnnotationRequest.model_validate(
        _request(boxes=[{"x": 0.1, "y": 0.2, "width": 0.4, "height": 0.3}])
    )

    assert auto_labeling._build_instances_conditioning(
        request=request, descriptor=_descriptor("points")
    )["points"] == [{"x": 0.30000000000000004, "y": 0.35, "positive": True}]


def test_instances_conditioning_marks_box_requests_as_all_instances() -> None:
    request = InstancesAnnotationRequest.model_validate(
        _request(
            prompt="cars",
            boxes=[{"x": 0.1, "y": 0.2, "width": 0.4, "height": 0.3}],
        )
    )

    assert auto_labeling._build_instances_conditioning(
        request=request, descriptor=_descriptor("instances")
    ) == {
        "instances": {
            "mode": "all",
            "prompt": "cars",
            "boxes": [{"x": 0.1, "y": 0.2, "width": 0.4, "height": 0.3}],
        }
    }


def test_interactive_box_conditioning_marks_request_as_single_instance() -> None:
    request = InteractiveAnnotationRequest.model_validate(
        _request(boxes=[{"x": 0.1, "y": 0.2, "width": 0.4, "height": 0.3}])
    )

    assert auto_labeling._build_interactive_conditioning(
        request=request, descriptor=_descriptor("instances")
    ) == {
        "instances": {
            "mode": "single",
            "boxes": [{"x": 0.1, "y": 0.2, "width": 0.4, "height": 0.3}],
        }
    }


def test_wire_task_keeps_a_task_the_model_serves() -> None:
    descriptor = _descriptor("targets")
    descriptor.capabilities = ["object_detection_image_bytes", "segmentation_image_bytes"]

    assert (
        auto_labeling.resolve_wire_task(descriptor=descriptor, task="object_detection")
        == "object_detection"
    )


def test_wire_task_asks_a_segmentation_only_model_for_masks() -> None:
    assert (
        auto_labeling.resolve_wire_task(descriptor=_descriptor("targets"), task="object_detection")
        == "segmentation"
    )
