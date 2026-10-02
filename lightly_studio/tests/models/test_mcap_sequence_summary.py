"""Tests for the MCAP sequence summary model."""

from __future__ import annotations

import pytest

from lightly_studio.models import mcap_sequence_summary


@pytest.mark.parametrize(
    ("uri", "expected"),
    [
        ("/bags/drive_001.mcap", "drive_001.mcap"),
        ("s3://bucket/path/drive.mcap", "drive.mcap"),
        ("C:\\bags\\drive.mcap", "drive.mcap"),
        ("C:/bags\\nested\\drive.mcap", "drive.mcap"),
        ("drive.mcap", "drive.mcap"),
    ],
)
def test_file_name_from_uri(uri: str, expected: str) -> None:
    assert mcap_sequence_summary._file_name_from_uri(uri) == expected
