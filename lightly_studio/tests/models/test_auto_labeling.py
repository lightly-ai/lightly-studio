from uuid import UUID

import pytest
from pydantic import ValidationError

from lightly_studio.models.auto_labeling import InteractiveAnnotationRequest


def _request(**conditioning: object) -> dict[str, object]:
    return {
        "collection_id": UUID("00000000-0000-0000-0000-000000000001"),
        "sample_id": UUID("00000000-0000-0000-0000-000000000002"),
        **conditioning,
    }


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
