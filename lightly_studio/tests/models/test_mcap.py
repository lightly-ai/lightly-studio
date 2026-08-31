"""Tests for the Mcap model."""

import pytest

from lightly_studio.models.mcap import McapCreate, McapDataType


class TestMcapCreate:
    """Tests for the McapCreate model."""

    def test_image__requires_keyframe_log_time_ns(self) -> None:
        """IMAGE locators must carry a GOP seek time."""
        with pytest.raises(ValueError, match="keyframe_log_time_ns is required"):
            McapCreate(
                mcap_data_type=McapDataType.IMAGE,
                channel_id=3,
                log_time_ns=100,
                capture_timestamp_ns=100,
            )

    def test_image__rejects_point_count(self) -> None:
        """IMAGE locators must not carry a point count."""
        with pytest.raises(ValueError, match="point_count must be None"):
            McapCreate(
                mcap_data_type=McapDataType.IMAGE,
                channel_id=3,
                log_time_ns=100,
                capture_timestamp_ns=100,
                keyframe_log_time_ns=90,
                point_count=11000,
            )

    def test_image__valid(self) -> None:
        """A well-formed IMAGE locator passes validation."""
        mcap = McapCreate(
            mcap_data_type=McapDataType.IMAGE,
            channel_id=3,
            log_time_ns=100,
            capture_timestamp_ns=100,
            keyframe_log_time_ns=90,
        )
        assert mcap.keyframe_log_time_ns == 90

    def test_point_cloud__rejects_keyframe_log_time_ns(self) -> None:
        """POINT_CLOUD locators have no GOP to seek, so no keyframe time."""
        with pytest.raises(ValueError, match="keyframe_log_time_ns must be None"):
            McapCreate(
                mcap_data_type=McapDataType.POINT_CLOUD,
                channel_id=5,
                log_time_ns=100,
                capture_timestamp_ns=100,
                keyframe_log_time_ns=90,
            )

    def test_point_cloud__valid(self) -> None:
        """A well-formed POINT_CLOUD locator passes validation."""
        mcap = McapCreate(
            mcap_data_type=McapDataType.POINT_CLOUD,
            channel_id=5,
            log_time_ns=100,
            capture_timestamp_ns=100,
            point_count=11000,
        )
        assert mcap.point_count == 11000
