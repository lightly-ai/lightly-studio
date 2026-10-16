from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from lightly_studio.models.assisted_labeling import (
    AnnotationBox,
    AnnotationPoint,
    InstancesAnnotationRequest,
    InteractiveAnnotationRequest,
)


class TestAnnotationBox:
    def test_validate_box(self) -> None:
        box = AnnotationBox(x=0.5, y=0.25, width=0.5, height=0.75)

        assert box == AnnotationBox(x=0.5, y=0.25, width=0.5, height=0.75)

    def test_validate_box__within_tolerance(self) -> None:
        box = AnnotationBox(x=0.5, y=0.5, width=0.5000001, height=0.5)

        assert box.width == 0.5000001

    @pytest.mark.parametrize(
        ("x", "y", "width", "height"),
        [(0.5, 0.5, 0.0, 0.5), (0.5, 0.5, 0.5, 0.0), (0.6, 0.5, 0.5, 0.5), (0.5, 0.6, 0.5, 0.5)],
    )
    def test_validate_box__invalid(self, x: float, y: float, width: float, height: float) -> None:
        with pytest.raises(ValidationError, match=r"The normalized box is empty or outside"):
            AnnotationBox(x=x, y=y, width=width, height=height)


class TestInteractiveAnnotationRequest:
    def test_validate_prompts__points(self) -> None:
        request = InteractiveAnnotationRequest(
            collection_id=uuid.uuid4(),
            sample_id=uuid.uuid4(),
            points=[AnnotationPoint(x=0.5, y=0.5, positive=True)],
        )

        assert request.boxes is None

    def test_validate_prompts__points_and_boxes(self) -> None:
        with pytest.raises(ValidationError, match="Provide either points or boxes"):
            InteractiveAnnotationRequest(
                collection_id=uuid.uuid4(),
                sample_id=uuid.uuid4(),
                points=[AnnotationPoint(x=0.5, y=0.5, positive=True)],
                boxes=[AnnotationBox(x=0.0, y=0.0, width=0.5, height=0.5)],
            )

    def test_validate_prompts__no_prompts(self) -> None:
        with pytest.raises(ValidationError, match="Provide either points or boxes"):
            InteractiveAnnotationRequest(collection_id=uuid.uuid4(), sample_id=uuid.uuid4())

    def test_validate_prompts__no_positive_point(self) -> None:
        with pytest.raises(ValidationError, match=r"Place at least one positive point\."):
            InteractiveAnnotationRequest(
                collection_id=uuid.uuid4(),
                sample_id=uuid.uuid4(),
                points=[AnnotationPoint(x=0.5, y=0.5, positive=False)],
            )

    def test_validate_prompts__too_many_points(self) -> None:
        with pytest.raises(ValidationError, match="at most 100 items"):
            InteractiveAnnotationRequest(
                collection_id=uuid.uuid4(),
                sample_id=uuid.uuid4(),
                points=[AnnotationPoint(x=0.5, y=0.5, positive=True)] * 101,
            )

    def test_validate_prompts__two_boxes(self) -> None:
        box = AnnotationBox(x=0.0, y=0.0, width=0.5, height=0.5)
        with pytest.raises(ValidationError, match="at most 1 item"):
            InteractiveAnnotationRequest(
                collection_id=uuid.uuid4(), sample_id=uuid.uuid4(), boxes=[box, box]
            )


class TestInstancesAnnotationRequest:
    def test_validate_prompts__blank_text_without_boxes(self) -> None:
        with pytest.raises(ValidationError, match=r"Provide a text prompt, boxes, or both\."):
            InstancesAnnotationRequest(
                collection_id=uuid.uuid4(), sample_id=uuid.uuid4(), prompt="   "
            )
