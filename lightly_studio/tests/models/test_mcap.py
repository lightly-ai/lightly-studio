"""Tests for the Mcap model."""

from lightly_studio.models.mcap import McapCreate


class TestMcapCreate:
    """Tests for the McapCreate model."""

    def test_image__valid(self) -> None:
        """A well-formed camera locator passes validation."""
        mcap = McapCreate(
            channel_id=3,
            log_time_ns=100,
            capture_timestamp_ns=100,
            keyframe_log_time_ns=90,
        )
        assert mcap.keyframe_log_time_ns == 90

    def test_point_cloud__valid(self) -> None:
        """A well-formed lidar locator passes validation."""
        mcap = McapCreate(
            channel_id=5,
            log_time_ns=100,
            capture_timestamp_ns=100,
            point_count=11000,
        )
        assert mcap.point_count == 11000
