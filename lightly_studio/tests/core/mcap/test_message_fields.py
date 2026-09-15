from __future__ import annotations

from types import SimpleNamespace

import pytest

from lightly_studio.core.mcap import message_fields
from lightly_studio.core.mcap.errors import McapAccessError


def test_get_field__attribute() -> None:
    message = SimpleNamespace(k=[1.0, 2.0])
    assert message_fields.get_field(message, ("k", "K")) == [1.0, 2.0]


def test_get_field__second_name() -> None:
    message = SimpleNamespace(K=[1.0, 2.0])
    assert message_fields.get_field(message, ("k", "K")) == [1.0, 2.0]


def test_get_field__mapping() -> None:
    assert message_fields.get_field({"K": [1.0]}, ("k", "K")) == [1.0]


def test_get_field__missing() -> None:
    assert message_fields.get_field(SimpleNamespace(width=1), ("k", "K")) is None
    assert message_fields.get_field({"width": 1}, ("k",)) is None


def test_require_field() -> None:
    assert message_fields.require_field({"width": 640}, ("width",)) == 640


def test_require_field__missing() -> None:
    with pytest.raises(McapAccessError, match="has no field 'k', 'K'"):
        message_fields.require_field(SimpleNamespace(width=1), ("k", "K"))
