from __future__ import annotations

import numpy as np

from lightly_studio_serve import PredictedAnnotation


class TestPredictedAnnotation:
    def test_eq(self) -> None:
        mask = np.array([[True, False, False], [False, True, True]], dtype=np.bool_)
        first = PredictedAnnotation(
            class_name="car", box=(0.0, 0.0, 3.0, 2.0), score=0.9, mask=mask
        )
        second = PredictedAnnotation(
            class_name="car", box=(0.0, 0.0, 3.0, 2.0), score=0.9, mask=mask.copy()
        )

        assert first == second
        assert second in [first]

    def test_eq__different_mask(self) -> None:
        first = PredictedAnnotation(
            class_name="car",
            box=(0.0, 0.0, 3.0, 2.0),
            score=0.9,
            mask=np.array([[True, False, False], [False, True, True]], dtype=np.bool_),
        )
        second = PredictedAnnotation(
            class_name="car",
            box=(0.0, 0.0, 3.0, 2.0),
            score=0.9,
            mask=np.array([[True, False, False], [False, True, False]], dtype=np.bool_),
        )

        assert first != second

    def test_eq__different_mask_shape(self) -> None:
        first = PredictedAnnotation(
            class_name="car",
            box=(0.0, 0.0, 3.0, 2.0),
            score=0.9,
            mask=np.ones((2, 3), dtype=np.bool_),
        )
        second = PredictedAnnotation(
            class_name="car",
            box=(0.0, 0.0, 3.0, 2.0),
            score=0.9,
            mask=np.ones((3, 2), dtype=np.bool_),
        )

        assert first != second

    def test_eq__mask_and_none(self) -> None:
        with_mask = PredictedAnnotation(
            class_name="car",
            box=(0.0, 0.0, 3.0, 2.0),
            score=0.9,
            mask=np.ones((2, 3), dtype=np.bool_),
        )
        without_mask = PredictedAnnotation(class_name="car", box=(0.0, 0.0, 3.0, 2.0), score=0.9)

        assert with_mask != without_mask
        assert without_mask != with_mask

    def test_eq__different_score(self) -> None:
        first = PredictedAnnotation(class_name="car", box=(0.0, 0.0, 3.0, 2.0), score=0.9)
        second = PredictedAnnotation(class_name="car", box=(0.0, 0.0, 3.0, 2.0), score=0.8)

        assert first != second

    def test_hash(self) -> None:
        mask = np.ones((2, 3), dtype=np.bool_)
        first = PredictedAnnotation(
            class_name="car", box=(0.0, 0.0, 3.0, 2.0), score=0.9, mask=mask
        )
        second = PredictedAnnotation(
            class_name="car", box=(0.0, 0.0, 3.0, 2.0), score=0.9, mask=mask.copy()
        )

        assert hash(first) == hash(second)
        assert len({first, second}) == 1
