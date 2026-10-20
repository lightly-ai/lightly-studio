from __future__ import annotations

import pytest
from pydantic import ValidationError

from lightly_studio.models.assisted_labeling import AnnotationBox


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
