from __future__ import annotations

import io

from PIL import Image

from tests.assisted_labeling import helpers


class TestLabelingImage:
    def test_to_pil(self) -> None:
        buffer = io.BytesIO()
        Image.new(mode="RGB", size=(4, 2), color=(255, 0, 0)).save(buffer, format="PNG")
        image = helpers.make_image(width=4, height=2, data=buffer.getvalue())

        pil_image = image.to_pil()

        assert pil_image.size == (4, 2)
        assert pil_image.getpixel((0, 0)) == (255, 0, 0)
