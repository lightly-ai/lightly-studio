"""Reads frame locators and calibration out of a local or remote MCAP file."""

from lightly_studio.core.mcap.reader.calibration import (
    DYNAMIC_TRANSFORM_TOPIC,
    STATIC_TRANSFORM_TOPIC,
)
from lightly_studio.core.mcap.reader.file_reader import McapFileReader
from lightly_studio.core.mcap.reader.session import ReadPattern

__all__ = [
    "DYNAMIC_TRANSFORM_TOPIC",
    "STATIC_TRANSFORM_TOPIC",
    "McapFileReader",
    "ReadPattern",
]
