from __future__ import annotations

from pathlib import Path

import pytest

from scripts import qa_pull


def test_validate_unique_triplets__rejects_same_delivery_in_two_prefixes() -> None:
    triplets = [
        _remote_triplet(prefix="review"),
        _remote_triplet(prefix="pool"),
    ]

    with pytest.raises(ValueError, match="multiple work prefixes"):
        qa_pull._validate_unique_triplets(triplets=triplets)


def test_cleanup_triplets__deletes_only_tracked_files(tmp_path: Path) -> None:
    destination = tmp_path / "pull"
    local_dir = destination / "bucket" / "clip"
    local_dir.mkdir(parents=True)
    video_path = local_dir / "clip.mp4"
    transcript_path = local_dir / "clip.faster-whisper.json"
    unrelated_path = local_dir / "notes.txt"
    for path in (video_path, transcript_path, unrelated_path):
        path.write_text("data")
    triplet = _local_triplet(
        video_path=video_path,
        transcript_path=transcript_path,
        local_files=(video_path, transcript_path),
    )

    deleted = qa_pull.cleanup_triplets(triplets=[triplet], destination=destination)

    assert deleted == 2
    assert not video_path.exists()
    assert not transcript_path.exists()
    assert unrelated_path.is_file()


def test_cleanup_triplets__rejects_path_outside_destination(tmp_path: Path) -> None:
    destination = tmp_path / "pull"
    destination.mkdir()
    outside_path = tmp_path / "outside.mp4"
    outside_path.write_text("data")
    triplet = _local_triplet(video_path=outside_path, local_files=(outside_path,))

    with pytest.raises(ValueError, match="outside destination"):
        qa_pull.cleanup_triplets(triplets=[triplet], destination=destination)

    assert outside_path.is_file()


def test_resolve_local_dir__rejects_stem_outside_destination(tmp_path: Path) -> None:
    triplet = qa_pull.RemoteTriplet(
        bucket="bucket",
        prefix="review",
        stem="../../escape",
        files=("gs://bucket/review/../../escape.mp4",),
    )

    with pytest.raises(ValueError, match="escapes destination"):
        qa_pull._resolve_local_dir(destination=tmp_path / "pull", triplet=triplet)


def _remote_triplet(prefix: str) -> qa_pull.RemoteTriplet:
    return qa_pull.RemoteTriplet(
        bucket="bucket",
        prefix=prefix,
        stem="clip",
        files=(f"gs://bucket/{prefix}/clip.mp4",),
    )


def _local_triplet(
    video_path: Path,
    transcript_path: Path | None = None,
    local_files: tuple[Path, ...] = (),
) -> qa_pull.LocalTriplet:
    return qa_pull.LocalTriplet(
        bucket="bucket",
        prefix="review",
        stem="clip",
        video_path=video_path,
        transcript_path=transcript_path,
        metadata_path=None,
        source_files=("gs://bucket/review/clip.mp4",),
        local_files=local_files,
    )
