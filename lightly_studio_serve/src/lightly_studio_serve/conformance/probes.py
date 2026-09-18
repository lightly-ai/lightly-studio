"""The fixed inputs a conformance run sends, and the bodies that carry them.

Each probe carries one item, so a server that reads the asset answers ``kept_indices ==
[0]``.
"""

from __future__ import annotations

import base64
from collections.abc import Mapping
from dataclasses import dataclass

from lightly_studio_serve import protocol
from lightly_studio_serve.embedder import Capability
from lightly_studio_serve.protocol import EmbedTextsRequest

# The example string of the protocol.
PROBE_TEXT = "a red car"

# An 8x8 RGB PNG. A literal, so the bytes never move: a later drift check compares runs.
PROBE_IMAGE = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAGUlEQVR42mNkYGhQYGDARCwMCgxYweCU"
    "AABobwJednxjlwAAAABJRU5ErkJggg=="
)

# One 16x16 H.264 frame in an MP4 container. 16x16 is one macroblock, the smallest
# picture H.264 codes without padding.
PROBE_VIDEO = base64.b64decode(
    "AAAAIGZ0eXBpc29tAAACAGlzb21pc28yYXZjMW1wNDEAAAAIZnJlZQAAAmxtZGF0AAACUQYF//9N3EXp"
    "vebZSLeWLNgg2SPu73gyNjQgLSBjb3JlIDE2NSAtIEguMjY0L01QRUctNCBBVkMgY29kZWMgLSBDb3B5"
    "bGVmdCAyMDAzLTIwMjUgLSBodHRwOi8vd3d3LnZpZGVvbGFuLm9yZy94MjY0Lmh0bWwgLSBvcHRpb25z"
    "OiBjYWJhYz0xIHJlZj0xIGRlYmxvY2s9MTowOjAgYW5hbHlzZT0weDM6MHgxMzMgbWU9dW1oIHN1Ym1l"
    "PTEwIHBzeT0xIHBzeV9yZD0xLjAwOjAuMDAgbWl4ZWRfcmVmPTAgbWVfcmFuZ2U9MjQgY2hyb21hX21l"
    "PTEgdHJlbGxpcz0yIDh4OGRjdD0xIGNxbT0wIGRlYWR6b25lPTIxLDExIGZhc3RfcHNraXA9MSBjaHJv"
    "bWFfcXBfb2Zmc2V0PS0yIHRocmVhZHM9MSBsb29rYWhlYWRfdGhyZWFkcz0xIHNsaWNlZF90aHJlYWRz"
    "PTAgbnI9MCBkZWNpbWF0ZT0xIGludGVybGFjZWQ9MCBibHVyYXlfY29tcGF0PTAgY29uc3RyYWluZWRf"
    "aW50cmE9MCBiZnJhbWVzPTAgd2VpZ2h0cD0wIGtleWludD0xIGtleWludF9taW49MSBzY2VuZWN1dD00"
    "MCBpbnRyYV9yZWZyZXNoPTAgcmM9Y3JmIG1idHJlZT0wIGNyZj01MS4wIHFjb21wPTAuNjAgcXBtaW49"
    "MCBxcG1heD02OSBxcHN0ZXA9NCBpcF9yYXRpbz0xLjQwIGFxPTE6MS4wMACAAAAAC2WIhP/w1HdBX7/B"
    "AAAC221vb3YAAABsbXZoZAAAAAAAAAAAAAAAAAAAA+gAAAPoAAEAAAEAAAAAAAAAAAAAAAABAAAAAAAA"
    "AAAAAAAAAAAAAQAAAAAAAAAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIAAAIq"
    "dHJhawAAAFx0a2hkAAAAAwAAAAAAAAAAAAAAAQAAAAAAAAPoAAAAAAAAAAAAAAAAAAAAAAABAAAAAAAA"
    "AAAAAAAAAAAAAQAAAAAAAAAAAAAAAAAAQAAAAAAQAAAAEAAAAAAAJGVkdHMAAAAcZWxzdAAAAAAAAAAB"
    "AAAD6AAAAAAAAQAAAAABom1kaWEAAAAgbWRoZAAAAAAAAAAAAAAAAAAAQAAAAEAAVcQAAAAAAC1oZGxy"
    "AAAAAAAAAAB2aWRlAAAAAAAAAAAAAAAAVmlkZW9IYW5kbGVyAAAAAU1taW5mAAAAFHZtaGQAAAABAAAA"
    "AAAAAAAAAAAkZGluZgAAABxkcmVmAAAAAAAAAAEAAAAMdXJsIAAAAAEAAAENc3RibAAAAKlzdHNkAAAA"
    "AAAAAAEAAACZYXZjMQAAAAAAAAABAAAAAAAAAAAAAAAAAAAAAAAQABAASAAAAEgAAAAAAAAAAQAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABj//wAAAC9hdmNDAWQQCv/hABJnZBAKrLvQgAAAAwCA"
    "AAADAQIBAAZo7gGUsiz9+PgAAAAAFGJ0cnQAAAAAAAATIAAAAAAAAAAYc3R0cwAAAAAAAAABAAAAAQAA"
    "QAAAAAAcc3RzYwAAAAAAAAABAAAAAQAAAAEAAAABAAAAFHN0c3oAAAAAAAACZAAAAAEAAAAUc3RjbwAA"
    "AAAAAAABAAAAMAAAAD11ZHRhAAAANW1ldGEAAAAAAAAAIWhkbHIAAAAAAAAAAG1kaXJhcHBsAAAAAAAA"
    "AAAAAAAACGlsc3Q="
)

# Long and specific, because a boundary that occurs in an asset cuts the part in two.
_BOUNDARY = "lightlystudioconformanceprobeboundary"


@dataclass(frozen=True)
class Probe:
    """One request a conformance run sends to test one capability."""

    path: str
    content_type: str
    body: bytes


def _multipart_probe(path: str, item: bytes, filename: str) -> Probe:
    """Frame one item for a bytes endpoint. A part without a filename reads as text."""
    body = b"".join(
        [
            f"--{_BOUNDARY}\r\n".encode(),
            f'Content-Disposition: form-data; name="{protocol.FILES_FIELD_NAME}"; '
            f'filename="{filename}"\r\n'.encode(),
            b"Content-Type: application/octet-stream\r\n\r\n",
            item,
            f"\r\n--{_BOUNDARY}--\r\n".encode(),
        ]
    )
    return Probe(path=path, content_type=f"multipart/form-data; boundary={_BOUNDARY}", body=body)


PROBES: Mapping[Capability, Probe] = {
    Capability.TEXT: Probe(
        path=protocol.EMBED_TEXTS_PATH,
        content_type="application/json",
        body=EmbedTextsRequest(texts=[PROBE_TEXT]).model_dump_json().encode(),
    ),
    Capability.IMAGE_BYTES: _multipart_probe(
        path=protocol.EMBED_IMAGES_BYTES_PATH, item=PROBE_IMAGE, filename="probe.png"
    ),
    Capability.VIDEO_BYTES: _multipart_probe(
        path=protocol.EMBED_VIDEOS_BYTES_PATH, item=PROBE_VIDEO, filename="probe.mp4"
    ),
}
"""The probe of every capability that crosses a wire in version 1."""
