from __future__ import annotations

import numpy as np

from lightly_studio.assisted_labeling.fake_provider import FakeProvider
from lightly_studio.assisted_labeling.provider import BoxPrompt, PointPrompt
from tests.assisted_labeling.helpers import make_image, make_prompt


class TestFakeProvider:
    def test_is_available(self) -> None:
        assert FakeProvider().is_available() is None
        assert FakeProvider().sends_data_to_third_party is False

    def test_segment__positive_points(self) -> None:
        # The radius is 10% of min(H, W) = 10 pixels.
        image = make_image(width=200, height=100)
        prompt = make_prompt(
            points=[PointPrompt(x=40, y=50, positive=True), PointPrompt(x=60, y=50, positive=True)]
        )

        predictions = FakeProvider().segment(image=image, prompt=prompt)

        assert len(predictions) == 1
        mask = predictions[0].mask
        assert mask.shape == (100, 200)
        assert mask.dtype == np.bool_
        assert mask[50, 50]
        assert mask[50, 60]
        assert not mask[50, 61]
        assert predictions[0].score == 0.9
        assert predictions[0].class_name is None

    def test_segment__negative_point_removes_pixels(self) -> None:
        image = make_image(width=100, height=100)
        prompt = make_prompt(
            points=[PointPrompt(x=50, y=50, positive=True), PointPrompt(x=55, y=50, positive=False)]
        )

        mask = FakeProvider().segment(image=image, prompt=prompt)[0].mask

        assert not mask[50, 55]
        assert mask[50, 41]

    def test_segment__only_negative_points(self) -> None:
        image = make_image(width=100, height=100)
        prompt = make_prompt(points=[PointPrompt(x=50, y=50, positive=False)])

        assert FakeProvider().segment(image=image, prompt=prompt) == []

    def test_segment__boxes(self) -> None:
        image = make_image(width=100, height=100)
        boxes = [
            BoxPrompt(x_min=10, y_min=10, x_max=30, y_max=30),
            BoxPrompt(x_min=60, y_min=60, x_max=90, y_max=80),
        ]

        predictions = FakeProvider().segment(
            image=image, prompt=make_prompt(boxes=boxes, max_masks=2)
        )

        assert len(predictions) == 2
        assert predictions[0].mask[20, 20]
        assert not predictions[0].mask[70, 75]
        assert predictions[1].mask[70, 75]
        assert not predictions[1].mask[10, 10]

    def test_segment__boxes_union(self) -> None:
        image = make_image(width=100, height=100)
        boxes = [
            BoxPrompt(x_min=10, y_min=10, x_max=30, y_max=30),
            BoxPrompt(x_min=60, y_min=60, x_max=90, y_max=80),
        ]

        predictions = FakeProvider().segment(
            image=image, prompt=make_prompt(boxes=boxes, max_masks=1)
        )

        assert len(predictions) == 1
        assert predictions[0].mask[20, 20]
        assert predictions[0].mask[70, 75]

    def test_segment__text(self) -> None:
        image = make_image(width=100, height=50)

        predictions = FakeProvider().segment(
            image=image, prompt=make_prompt(text="car", max_masks=10)
        )

        assert len(predictions) == 3
        assert [prediction.class_name for prediction in predictions] == ["car", "car", "car"]
        assert all(prediction.mask.shape == (50, 100) for prediction in predictions)
        assert predictions[0].mask[25, 25]
        assert predictions[1].mask[25, 50]
        assert predictions[2].mask[25, 75]

    def test_segment__text_max_masks(self) -> None:
        image = make_image(width=100, height=50)

        predictions = FakeProvider().segment(
            image=image, prompt=make_prompt(text="car", max_masks=2)
        )

        assert len(predictions) == 2

    def test_segment__deterministic(self) -> None:
        image = make_image(width=64, height=48)
        prompt = make_prompt(text="car", max_masks=3)

        first = FakeProvider().segment(image=image, prompt=prompt)
        second = FakeProvider().segment(image=image, prompt=prompt)

        for first_prediction, second_prediction in zip(first, second):
            np.testing.assert_array_equal(first_prediction.mask, second_prediction.mask)
