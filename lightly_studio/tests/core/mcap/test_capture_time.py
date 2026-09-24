from __future__ import annotations

from types import SimpleNamespace

import pytest

from lightly_studio.core.mcap import capture_time
from lightly_studio.core.mcap.errors import McapAccessError


def test_from_decoded_message__header_stamp() -> None:
    message = SimpleNamespace(header=SimpleNamespace(stamp=SimpleNamespace(sec=1, nanosec=50)))

    assert capture_time.from_decoded_message(message) == 1_000_000_050


def test_from_decoded_message__foxglove_timestamp() -> None:
    message = SimpleNamespace(timestamp=SimpleNamespace(sec=2, nsec=100))

    assert capture_time.from_decoded_message(message) == 2_000_000_100


def test_from_decoded_message__protobuf_timestamp() -> None:
    message = {"timestamp": {"seconds": 2, "nanos": 100}}

    assert capture_time.from_decoded_message(message) == 2_000_000_100


def test_from_decoded_message__missing() -> None:
    with pytest.raises(McapAccessError, match="header stamp or timestamp"):
        capture_time.from_decoded_message(SimpleNamespace(frame_id="odom"))


def test_from_decoded_message__not_a_number() -> None:
    with pytest.raises(McapAccessError, match="not a number"):
        capture_time.from_decoded_message({"timestamp": {"sec": "invalid"}})
