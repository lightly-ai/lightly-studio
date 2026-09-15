"""Reads a real recording, e.g. `perception.mcap`, if one is available.

Point `LIGHTLY_STUDIO_TEST_MCAP_PATH` at an indexed MCAP file to run these tests:

    LIGHTLY_STUDIO_TEST_MCAP_PATH=/data/perception.mcap uv run pytest \
        tests/core/mcap/test_reader_integration.py

Point the topic env vars below at topics of that recording to run the tests that need
them. A test whose topic env var is unset is skipped, because the topics of a recording
are not known in advance.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from lightly_studio.core.mcap.reader import McapFileReader

MCAP_PATH_ENV_VAR = "LIGHTLY_STUDIO_TEST_MCAP_PATH"
VIDEO_TOPIC_ENV_VAR = "LIGHTLY_STUDIO_TEST_MCAP_VIDEO_TOPIC"


@pytest.fixture
def reader() -> Iterator[McapFileReader]:
    path = os.environ.get(MCAP_PATH_ENV_VAR)
    if path is None:
        pytest.skip(f"Set {MCAP_PATH_ENV_VAR} to an MCAP file to run this test.")
    with McapFileReader(Path(path)) as mcap_file_reader:
        yield mcap_file_reader


def _require_env(env_var: str) -> str:
    value = os.environ.get(env_var)
    if value is None:
        pytest.skip(f"Set {env_var} to run this test.")
    return value


def test_get_frame_locators(reader: McapFileReader) -> None:
    topic = _require_env(VIDEO_TOPIC_ENV_VAR)
    reader.load_data_for_topics([topic])

    locators = reader.get_frame_locators(topic)

    assert locators
    assert [locator.log_time_ns for locator in locators] == sorted(
        locator.log_time_ns for locator in locators
    )


def test_get_frame_locators__video_keyframes(reader: McapFileReader) -> None:
    topic = _require_env(VIDEO_TOPIC_ENV_VAR)
    reader.load_data_for_topics([topic])

    locators = reader.get_frame_locators(topic)

    keyframe_log_times_ns = {
        locator.keyframe_log_time_ns
        for locator in locators
        if locator.keyframe_log_time_ns is not None
    }
    assert keyframe_log_times_ns
    assert keyframe_log_times_ns <= {locator.log_time_ns for locator in locators}


def test_get_frame_locators__sync_timestamps(reader: McapFileReader) -> None:
    topic = _require_env(VIDEO_TOPIC_ENV_VAR)
    reader.load_data_for_topics([topic])
    locators = reader.get_frame_locators(topic)
    timestamps_ns = [locator.log_time_ns for locator in locators[:5]]

    matched = reader.get_frame_locators(topic, sync_timestamps=timestamps_ns)

    assert matched == locators[:5]
