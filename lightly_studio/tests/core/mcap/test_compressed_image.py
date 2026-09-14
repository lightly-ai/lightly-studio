import struct

from lightly_studio.core.mcap.compressed_image import decode_compressed_image


def test_decode_compressed_image() -> None:
    payload = b"\x89PNG\r\n"
    data = b"\x00\x01\x00\x00" + struct.pack("<q", 123)
    data += struct.pack("<I", 5) + b"frame"
    data += struct.pack("<I", 3) + b"png"
    data += struct.pack("<I", len(payload)) + payload

    image, media_type = decode_compressed_image(data)

    assert image == payload
    assert media_type == "image/png"


def test_decode_compressed_image_rejects_unsupported_format() -> None:
    data = b"\x00\x01\x00\x00" + struct.pack("<q", 123)
    data += struct.pack("<I", 1) + b"f"
    data += struct.pack("<I", 3) + b"raw"
    data += struct.pack("<I", 0)

    try:
        decode_compressed_image(data)
    except ValueError as error:
        assert "Unsupported compressed image format" in str(error)
    else:
        raise AssertionError("Expected unsupported image format to fail")
