from __future__ import annotations

from uuid import uuid4

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

        assert box.x + box.width == 1.0

    @pytest.mark.parametrize(
        ("x", "y", "width", "height"),
        [(0.5, 0.5, 0.0, 0.5), (0.5, 0.5, 0.5, 0.0), (0.6, 0.5, 0.5, 0.5), (0.5, 0.6, 0.5, 0.5)],
    )
    def test_validate_box__invalid(self, x: float, y: float, width: float, height: float) -> None:
        with pytest.raises(ValidationError, match=r"The normalized box is invalid\."):
            AnnotationBox(x=x, y=y, width=width, height=height)


class TestInteractiveAnnotationRequest:
    def test_validate_prompts__points(self) -> None:
        request = InteractiveAnnotationRequest(
            collection_id=uuid4(),
            sample_id=uuid4(),
            points=[AnnotationPoint(x=0.5, y=0.5, positive=True)],
        )

        assert request.boxes is None

    def test_validate_prompts__points_and_boxes(self) -> None:
        with pytest.raises(ValidationError, match="Provide either points or boxes"):
            InteractiveAnnotationRequest(
                collection_id=uuid4(),
                sample_id=uuid4(),
                points=[AnnotationPoint(x=0.5, y=0.5, positive=True)],
                boxes=[AnnotationBox(x=0.0, y=0.0, width=0.5, height=0.5)],
            )

    def test_validate_prompts__no_prompts(self) -> None:
        with pytest.raises(ValidationError, match="Provide either points or boxes"):
            InteractiveAnnotationRequest(collection_id=uuid4(), sample_id=uuid4())

    def test_validate_prompts__no_positive_point(self) -> None:
        with pytest.raises(ValidationError, match=r"Place at least one positive point\."):
            InteractiveAnnotationRequest(
                collection_id=uuid4(),
                sample_id=uuid4(),
                points=[AnnotationPoint(x=0.5, y=0.5, positive=False)],
            )


class TestInstancesAnnotationRequest:
    def test_validate_prompts__text(self) -> None:
        request = InstancesAnnotationRequest(collection_id=uuid4(), sample_id=uuid4(), prompt="dog")

        assert request.max_instances == 16

    def test_validate_prompts__blank_text(self) -> None:
        with pytest.raises(ValidationError, match=r"Provide a text prompt, boxes, or both\."):
            InstancesAnnotationRequest(collection_id=uuid4(), sample_id=uuid4(), prompt="  ")

    def test_validate_prompts__boxes(self) -> None:
        request = InstancesAnnotationRequest(
            collection_id=uuid4(),
            sample_id=uuid4(),
            boxes=[AnnotationBox(x=0.0, y=0.0, width=0.5, height=0.5)],
        )

        assert request.prompt is None
