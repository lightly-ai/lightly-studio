"""Tests for compressed_image.py — decoding CompressedImage messages."""

from __future__ import annotations

import io
from types import SimpleNamespace

import pytest
from PIL import Image

from lightly_studio.core.mcap import compressed_image
from lightly_studio.core.mcap.errors import McapAccessError
from tests.core.mcap import helpers


def test_to_jpeg__jpeg_at_original_size_is_unchanged() -> None:
    data = helpers.encoded_image(gray_level=128, width=16, height=8)
    message = SimpleNamespace(data=data, format="jpeg")

    assert compressed_image.to_jpeg(decoded_message=message, quality=10) == data


def test_to_jpeg__dict_message() -> None:
    data = helpers.encoded_image(gray_level=128)

    assert compressed_image.to_jpeg(decoded_message={"data": data, "format": "jpeg"}) == data


def test_to_jpeg__resize_width() -> None:
    message = SimpleNamespace(data=helpers.encoded_image(gray_level=128, width=32, height=16))

    data = compressed_image.to_jpeg(decoded_message=message, width=8)

    assert _image_size(data) == (8, 4)
    assert 96 < helpers.jpeg_mean_gray_level(data) < 160


def test_to_jpeg__resize_height() -> None:
    message = SimpleNamespace(data=helpers.encoded_image(gray_level=128, width=32, height=16))

    data = compressed_image.to_jpeg(decoded_message=message, height=4)

    assert _image_size(data) == (8, 4)


def test_to_jpeg__resize_both() -> None:
    message = SimpleNamespace(data=helpers.encoded_image(gray_level=128, width=32, height=16))

    data = compressed_image.to_jpeg(decoded_message=message, width=10, height=10)

    assert _image_size(data) == (10, 10)


def test_to_jpeg__png_is_encoded_as_jpeg() -> None:
    message = SimpleNamespace(
        data=helpers.encoded_image(gray_level=255, width=16, height=8, image_format="PNG"),
        format="png",
    )

    data = compressed_image.to_jpeg(decoded_message=message)

    image = Image.open(io.BytesIO(data))
    assert image.format == "JPEG"
    assert image.size == (16, 8)
    assert helpers.jpeg_mean_gray_level(data) > 223


def test_to_jpeg__missing_data_field() -> None:
    with pytest.raises(McapAccessError, match="'data'"):
        compressed_image.to_jpeg(decoded_message=SimpleNamespace(format="jpeg"))


def test_to_jpeg__non_bytes_data() -> None:
    with pytest.raises(McapAccessError, match="non-bytes 'data' field"):
        compressed_image.to_jpeg(decoded_message=SimpleNamespace(data="not bytes"))


def test_to_jpeg__undecodable_payload() -> None:
    # A raw image is not an encoded file.
    message = SimpleNamespace(data=bytes(16 * 16 * 3))

    with pytest.raises(McapAccessError, match="Only encoded pictures"):
        compressed_image.to_jpeg(decoded_message=message)


def test_to_jpeg__truncated_payload() -> None:
    data = helpers.encoded_image(gray_level=128, width=32, height=32, image_format="PNG")
    message = SimpleNamespace(data=data[: len(data) // 2])

    with pytest.raises(McapAccessError, match="Cannot decode"):
        compressed_image.to_jpeg(decoded_message=message, width=8)


def test_to_image() -> None:
    message = SimpleNamespace(data=helpers.encoded_image(gray_level=128, width=16, height=8))

    image = compressed_image.to_image(decoded_message=message)

    assert image.mode == "RGB"
    assert image.size == (16, 8)


def test_to_image__grayscale_png_is_rgb() -> None:
    output = io.BytesIO()
    Image.new(mode="L", size=(4, 2), color=200).save(output, format="PNG")
    message = SimpleNamespace(data=output.getvalue())

    image = compressed_image.to_image(decoded_message=message)

    assert image.mode == "RGB"
    assert image.getpixel((0, 0)) == (200, 200, 200)


def test_to_image__scales_to_width() -> None:
    message = SimpleNamespace(data=helpers.encoded_image(gray_level=128, width=32, height=16))

    image = compressed_image.to_image(decoded_message=message, width=8)

    assert image.mode == "RGB"
    assert image.size == (8, 4)


def _image_size(data: bytes) -> tuple[int, int]:
    return Image.open(io.BytesIO(data)).size
