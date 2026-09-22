from __future__ import annotations

import io

from PIL import Image

from lightly_studio_serve.conformance import probes
from lightly_studio_serve.embedder import Capability


def test_probes__one_per_capability_that_crosses_a_wire() -> None:
    assert set(probes.PROBES) == {
        Capability.TEXT,
        Capability.IMAGE_BYTES,
        Capability.VIDEO_BYTES,
    }


def test_probes__text_body() -> None:
    assert probes.PROBES[Capability.TEXT].body == b'{"texts":["a red car"]}'


def test_probes__image_body_frames_the_asset() -> None:
    """The framing is the protocol, so the kit writes it rather than a client package."""
    probe = probes.PROBES[Capability.IMAGE_BYTES]

    assert probe.content_type == (
        "multipart/form-data; boundary=lightlystudioconformanceprobeboundary"
    )
    assert probe.body == (
        b"--lightlystudioconformanceprobeboundary\r\n"
        b'Content-Disposition: form-data; name="files"; filename="probe.png"\r\n'
        b"Content-Type: application/octet-stream\r\n\r\n"
        + probes.PROBE_IMAGE
        + b"\r\n--lightlystudioconformanceprobeboundary--\r\n"
    )


def test_probes__boundary_is_not_in_an_asset() -> None:
    """A boundary that occurs in a payload cuts the part in two."""
    boundary = probes._BOUNDARY.encode()

    assert boundary not in probes.PROBE_IMAGE
    assert boundary not in probes.PROBE_VIDEO


def test_probe_image__is_an_8x8_png() -> None:
    with Image.open(io.BytesIO(probes.PROBE_IMAGE)) as image:
        assert image.format == "PNG"
        assert image.size == (8, 8)


def test_probe_video__is_an_mp4() -> None:
    """The header of the asset, which is what a server sniffs the format from."""
    assert probes.PROBE_VIDEO[4:12] == b"ftypisom"


def test_probe_video__holds_one_frame() -> None:
    """``stsz`` holds a version, a sample size and then the count. One sample is a frame."""
    box = probes.PROBE_VIDEO.index(b"stsz")

    assert int.from_bytes(probes.PROBE_VIDEO[box + 12 : box + 16], byteorder="big") == 1
