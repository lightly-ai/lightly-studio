"""Unit tests for the shared media executor registry."""

from __future__ import annotations

import lightly_studio.utils.executor as executor_module
from lightly_studio.utils.executor import _get_media_executor


def setup_function() -> None:
    executor_module._executors.clear()


def test__get_media_executor_is_singleton_per_prefix() -> None:
    # The registry must return the same instance on repeated calls so threads
    # are shared rather than a new pool being created on every request.
    executor1 = _get_media_executor("image_thumbnail")
    executor2 = _get_media_executor("image_thumbnail")

    assert executor1 is executor2


def test__get_media_executor_isolates_different_prefixes() -> None:
    # Each prefix gets its own pool so image and video workers don't compete
    # for the same slots.
    image_executor = _get_media_executor("image_thumbnail")
    video_executor = _get_media_executor("video_frame")

    assert image_executor is not video_executor
