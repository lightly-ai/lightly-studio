"""Tests for decoded ROS message field access."""

from collections import UserDict
from types import SimpleNamespace

from lightly_studio.services.recording_service import point_cloud_value


def test_get_value__mapping() -> None:
    assert point_cloud_value.get_value(value={"name": "x"}, name="name") == "x"


def test_get_value__mapping_non_dict() -> None:
    value: UserDict[str, str] = UserDict({"name": "x"})

    assert point_cloud_value.get_value(value=value, name="name") == "x"


def test_get_value__object() -> None:
    value = SimpleNamespace(name="x")

    assert point_cloud_value.get_value(value=value, name="name") == "x"
