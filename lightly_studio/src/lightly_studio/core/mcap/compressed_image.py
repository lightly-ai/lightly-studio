"""Decoding displayable frames from compressed image messages.

Handles `sensor_msgs/msg/CompressedImage` and the equivalent Foxglove schema. Each
message carries one complete encoded picture in `data`, e.g. a JPEG or a PNG file, so
every message decodes on its own and is its own keyframe. The `format` field, e.g.
`"jpeg"` or `"rgb8; jpeg compressed bgr8"`, is not read: Pillow detects the encoding
from the payload.
"""

from __future__ import annotations

import io
from typing import Any

from PIL import Image, UnidentifiedImageError

from lightly_studio.core.mcap import _video_formats, message_fields
from lightly_studio.core.mcap.compressed_video import JPEG_QUALITY
from lightly_studio.core.mcap.errors import McapAccessError


def to_jpeg(
    decoded_message: Any,
    width: int | None = None,
    height: int | None = None,
    quality: int = JPEG_QUALITY,
) -> bytes:
    """Returns the picture of a compressed image message as JPEG.

    A JPEG payload at its original size is returned unchanged, without encoding it
    again, so `quality` has no effect on it.

    Args:
        decoded_message: A decoded compressed image message with a `data` field.
        width: If set, resize the output to this width in pixels. Aspect ratio is
            preserved when only one of `width` / `height` is given.
        height: If set, resize the output to this height in pixels. Aspect ratio is
            preserved when only one of `width` / `height` is given.
        quality: JPEG quality (1-95). Defaults to `JPEG_QUALITY`.

    Returns:
        JPEG-encoded bytes of the picture.

    Raises:
        McapAccessError: If the message has no `data` field, or Pillow cannot decode
            the payload.
    """
    data = _payload(decoded_message=decoded_message)
    picture = _open(data=data)
    out_size = _output_size(size=picture.size, width=width, height=height)
    if picture.format == "JPEG" and out_size == picture.size:
        return data
    output = io.BytesIO()
    _scaled_rgb(picture=picture, width=width, height=height).save(
        output, format="JPEG", quality=min(95, max(1, quality))
    )
    return output.getvalue()


def to_image(
    decoded_message: Any,
    width: int | None = None,
    height: int | None = None,
) -> Image.Image:
    """Decodes the picture of a compressed image message to an RGB image.

    Args:
        decoded_message: A decoded compressed image message with a `data` field.
        width: If set, resize the output to this width in pixels. Aspect ratio is
            preserved when only one of `width` / `height` is given.
        height: If set, resize the output to this height in pixels. Aspect ratio is
            preserved when only one of `width` / `height` is given.

    Returns:
        The decoded picture in RGB mode. At its original size when `width` and
        `height` are both omitted.

    Raises:
        McapAccessError: If the message has no `data` field, or Pillow cannot decode
            the payload.
    """
    picture = _open(data=_payload(decoded_message=decoded_message))
    return _scaled_rgb(picture=picture, width=width, height=height)


def _payload(decoded_message: Any) -> bytes:
    """Returns the encoded picture of a compressed image message.

    Raises:
        McapAccessError: If the message has no `data` field, or it is not bytes.
    """
    data = message_fields.require_field(decoded_message, _video_formats.DATA_FIELDS)
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise McapAccessError(
            f"Compressed image message has a non-bytes 'data' field: {type(data).__name__}."
        )
    return bytes(data)


def _open(data: bytes) -> Image.Image:
    """Opens an encoded picture. Only the file header is read, not the pixels.

    Raises:
        McapAccessError: If Pillow cannot identify the payload, e.g. because it is a
            raw image and not an encoded file.
    """
    try:
        return Image.open(io.BytesIO(data))
    except (UnidentifiedImageError, OSError) as exc:
        raise McapAccessError(
            f"Cannot decode the compressed image payload. Only encoded pictures, e.g. "
            f"JPEG or PNG, are supported: {exc}"
        ) from exc


def _scaled_rgb(picture: Image.Image, width: int | None, height: int | None) -> Image.Image:
    """Decodes a picture to RGB and scales it to the output size.

    Raises:
        McapAccessError: If the pixels of the picture cannot be decoded, e.g. because
            the file is truncated.
    """
    try:
        rgb = picture.convert("RGB")
    except OSError as exc:
        raise McapAccessError(f"Cannot decode the compressed image payload: {exc}") from exc
    out_size = _output_size(size=rgb.size, width=width, height=height)
    if out_size == rgb.size:
        return rgb
    resample = (
        Image.Resampling.BOX
        if out_size[0] <= rgb.width and out_size[1] <= rgb.height
        else Image.Resampling.BILINEAR
    )
    return rgb.resize(out_size, resample=resample)


def _output_size(size: tuple[int, int], width: int | None, height: int | None) -> tuple[int, int]:
    """Returns the output size, preserving aspect ratio when one side is omitted."""
    source_width, source_height = size
    if width is None and height is None:
        return source_width, source_height
    if width is None:
        assert height is not None
        return max(1, round(source_width * height / source_height)), height
    if height is None:
        return width, max(1, round(source_height * width / source_width))
    return width, height
