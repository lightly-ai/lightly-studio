from __future__ import annotations

from pathlib import Path

import pytest

from auto_qa import storage


def test_deduplicate_keeps_first_prefix() -> None:
    deliveries = [_remote(prefix="review"), _remote(prefix="pool")]

    assert storage._deduplicate(deliveries) == [deliveries[0]]


def test_cleanup_deletes_only_tracked_files(tmp_path: Path) -> None:
    destination = tmp_path / "pull"
    destination.mkdir()
    video = destination / "clip.mp4"
    transcript = destination / "clip.json"
    unrelated = destination / "notes.txt"
    for path in (video, transcript, unrelated):
        path.write_text("data")
    delivery = _local(video=video, transcript=transcript, files=(video, transcript))

    assert storage.cleanup([delivery], destination) == 2
    assert unrelated.is_file()
    assert not video.exists()
    assert not transcript.exists()


def test_cleanup_rejects_path_outside_destination(tmp_path: Path) -> None:
    destination = tmp_path / "pull"
    destination.mkdir()
    outside = tmp_path / "outside.mp4"
    outside.write_text("data")

    with pytest.raises(ValueError, match="outside destination"):
        storage.cleanup([_local(video=outside, files=(outside,))], destination)

    assert outside.is_file()


def test_local_directory_rejects_unsafe_stem(tmp_path: Path) -> None:
    delivery = storage.RemoteDelivery(
        bucket="bucket",
        prefix="review",
        stem="../../escape",
        files=("gs://bucket/review/../../escape.mp4",),
    )

    with pytest.raises(ValueError, match="escapes destination"):
        storage._local_directory(tmp_path / "pull", delivery)


def _remote(prefix: str) -> storage.RemoteDelivery:
    return storage.RemoteDelivery(
        bucket="bucket",
        prefix=prefix,
        stem="clip",
        files=(f"gs://bucket/{prefix}/clip.mp4",),
    )


def _local(
    video: Path,
    transcript: Path | None = None,
    files: tuple[Path, ...] = (),
) -> storage.LocalDelivery:
    return storage.LocalDelivery(
        bucket="bucket",
        prefix="review",
        stem="clip",
        video_path=video,
        transcript_path=transcript,
        source_files=("gs://bucket/review/clip.mp4",),
        local_files=files,
    )
