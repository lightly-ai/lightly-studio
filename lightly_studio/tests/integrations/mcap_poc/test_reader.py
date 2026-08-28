"""Tests for indexed MCAP reading and the benchmark measurements."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

from lightly_studio.integrations.mcap_poc import reader


def test_describe_source_lists_point_cloud_topics(point_cloud_mcap: Path) -> None:
    description = reader.describe_source(source=str(point_cloud_mcap))

    assert description.size_bytes == point_cloud_mcap.stat().st_size
    assert description.topics == [
        reader.McapTopic(topic="/lidar/points", message_count=2, first_log_time_ns=100)
    ]


def test_describe_source_rejects_a_recording_without_point_clouds(string_only_mcap: Path) -> None:
    with pytest.raises(ValueError, match="no ROS 2 PointCloud2 topics"):
        reader.describe_source(source=str(string_only_mcap))


def test_read_frame_returns_the_first_frame_at_or_after_the_timestamp(
    point_cloud_mcap: Path,
) -> None:
    result = reader.read_point_cloud_frame(
        source=str(point_cloud_mcap), topic="/lidar/points", timestamp_ns=150
    )

    assert result.log_time_ns == 200
    assert result.point_count == 1
    np.testing.assert_array_equal(
        np.frombuffer(result.content, dtype="<f4"), np.asarray([8, 9, 10, 11], dtype=np.float32)
    )


def test_read_frame_drops_non_finite_points(point_cloud_mcap: Path) -> None:
    result = reader.read_point_cloud_frame(
        source=str(point_cloud_mcap), topic="/lidar/points", timestamp_ns=0
    )

    assert result.log_time_ns == 100
    assert result.point_count == 1
    np.testing.assert_array_equal(
        np.frombuffer(result.content, dtype="<f4"), np.asarray([1, 2, 3, 4], dtype=np.float32)
    )


def test_read_frame_reuses_the_summary_index_between_calls(point_cloud_mcap: Path) -> None:
    first = reader.read_point_cloud_frame(
        source=str(point_cloud_mcap), topic="/lidar/points", timestamp_ns=0
    )
    second = reader.read_point_cloud_frame(
        source=str(point_cloud_mcap), topic="/lidar/points", timestamp_ns=0
    )

    assert first.index_cached is False
    assert first.index_time_ms > 0
    assert second.index_cached is True
    assert second.index_time_ms == 0


def test_read_frame_counts_only_the_bytes_read_for_that_frame(point_cloud_mcap: Path) -> None:
    first = reader.read_point_cloud_frame(
        source=str(point_cloud_mcap), topic="/lidar/points", timestamp_ns=0
    )
    second = reader.read_point_cloud_frame(
        source=str(point_cloud_mcap), topic="/lidar/points", timestamp_ns=0
    )

    assert second.read_count == first.read_count
    assert second.bytes_read == first.bytes_read


def test_read_frame_can_measure_a_cold_read(point_cloud_mcap: Path) -> None:
    reader.read_point_cloud_frame(
        source=str(point_cloud_mcap), topic="/lidar/points", timestamp_ns=0
    )
    cold = reader.read_point_cloud_frame(
        source=str(point_cloud_mcap), topic="/lidar/points", timestamp_ns=0, reuse_index=False
    )

    assert cold.index_cached is False
    assert cold.index_time_ms > 0


def test_clear_source_cache_forces_the_next_read_to_reindex(point_cloud_mcap: Path) -> None:
    reader.read_point_cloud_frame(
        source=str(point_cloud_mcap), topic="/lidar/points", timestamp_ns=0
    )
    reader.clear_source_cache()
    result = reader.read_point_cloud_frame(
        source=str(point_cloud_mcap), topic="/lidar/points", timestamp_ns=0
    )

    assert result.index_cached is False


def test_read_frame_reindexes_when_the_local_file_is_replaced(
    point_cloud_mcap: Path, tmp_path: Path
) -> None:
    source = tmp_path / "rolling.mcap"
    source.write_bytes(point_cloud_mcap.read_bytes())
    reader.read_point_cloud_frame(source=str(source), topic="/lidar/points", timestamp_ns=0)
    modified_ns = source.stat().st_mtime_ns + 1_000_000_000
    os.utime(source, ns=(modified_ns, modified_ns))

    result = reader.read_point_cloud_frame(
        source=str(source), topic="/lidar/points", timestamp_ns=0
    )

    assert result.index_cached is False


def test_read_frame_rejects_a_timestamp_after_the_last_message(point_cloud_mcap: Path) -> None:
    with pytest.raises(ValueError, match="No message found for topic"):
        reader.read_point_cloud_frame(
            source=str(point_cloud_mcap), topic="/lidar/points", timestamp_ns=10_000
        )


def test_local_source_path_resolves_local_sources_only(point_cloud_mcap: Path) -> None:
    assert reader.local_source_path(source=str(point_cloud_mcap)) == point_cloud_mcap
    assert reader.local_source_path(source="https://example.test/a.mcap") is None


def test_local_source_path_rejects_a_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="does not exist"):
        reader.local_source_path(source=str(tmp_path / "missing.mcap"))
