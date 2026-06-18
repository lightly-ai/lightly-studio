from __future__ import annotations

from pathlib import Path

from lightly_studio import ImageDataset
from tests.resolvers.video.helpers import create_video_file


def test_add_frames_from_videos__all_frames(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    videos_dir = tmp_path / "videos"
    create_video_file(
        output_path=videos_dir / "clip.mp4", width=64, height=64, num_frames=30, fps=10
    )
    extract_dir = tmp_path / "frames"

    dataset = ImageDataset.create(name="test_dataset")
    created_ids = dataset.add_frames_from_videos(
        videos_path=videos_dir, extract_dir=extract_dir, fps=None, embed=False
    )

    # All decoded frames are extracted and added.
    assert len(created_ids) == 30
    assert len(dataset.query().to_list()) == 30
    # Frames are written to disk under a per-video subdirectory.
    assert len(list((extract_dir / "clip").glob("*.jpg"))) == 30


def test_add_frames_from_videos__fps_subsamples(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    # 30 frames at 10 fps == 3 seconds of footage.
    videos_dir = tmp_path / "videos"
    create_video_file(
        output_path=videos_dir / "clip.mp4", width=64, height=64, num_frames=30, fps=10
    )

    dataset_low = ImageDataset.create(name="low_fps")
    low_ids = dataset_low.add_frames_from_videos(
        videos_path=videos_dir, extract_dir=tmp_path / "low", fps=2, embed=False
    )

    dataset_high = ImageDataset.create(name="high_fps")
    high_ids = dataset_high.add_frames_from_videos(
        videos_path=videos_dir, extract_dir=tmp_path / "high", fps=5, embed=False
    )

    # Sub-sampling keeps fewer frames, and a higher fps keeps more of them.
    assert len(low_ids) < len(high_ids) <= 30
    # ~2 fps over 3 seconds -> roughly 6 frames (allow rounding slack).
    assert 5 <= len(low_ids) <= 7


def test_add_frames_from_videos__tags_with_video_stem(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    videos_dir = tmp_path / "videos"
    create_video_file(
        output_path=videos_dir / "my_clip.mp4", width=64, height=64, num_frames=4, fps=2
    )

    dataset = ImageDataset.create(name="test_dataset")
    dataset.add_frames_from_videos(
        videos_path=videos_dir, extract_dir=tmp_path / "frames", fps=None, embed=False
    )

    samples = dataset.query().to_list()
    assert samples
    assert all("my_clip" in sample.tags for sample in samples)


def test_add_frames_from_videos__multiple_videos(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    videos_dir = tmp_path / "videos"
    create_video_file(
        output_path=videos_dir / "clip_a.mp4", width=64, height=64, num_frames=4, fps=2
    )
    create_video_file(
        output_path=videos_dir / "clip_b.mp4", width=64, height=64, num_frames=6, fps=2
    )

    dataset = ImageDataset.create(name="test_dataset")
    created_ids = dataset.add_frames_from_videos(
        videos_path=videos_dir, extract_dir=tmp_path / "frames", fps=None, embed=False
    )

    # Both videos are processed in a single call.
    assert len(created_ids) == 4 + 6
    samples = dataset.query().to_list()
    # Each video's frames are tagged with that video's stem.
    assert len([s for s in samples if "clip_a" in s.tags]) == 4
    assert len([s for s in samples if "clip_b" in s.tags]) == 6


def test_add_frames_from_videos__skips_already_processed(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    videos_dir = tmp_path / "videos"
    create_video_file(output_path=videos_dir / "clip.mp4", width=64, height=64, num_frames=4, fps=2)

    dataset = ImageDataset.create(name="test_dataset")
    first_ids = dataset.add_frames_from_videos(
        videos_path=videos_dir, extract_dir=tmp_path / "frames", fps=None, embed=False
    )
    assert len(first_ids) == 4

    # The video already has its stem tag, so a second run adds nothing.
    second_ids = dataset.add_frames_from_videos(
        videos_path=videos_dir, extract_dir=tmp_path / "frames_2", fps=None, embed=False
    )
    assert second_ids == []
    assert len(dataset.query().to_list()) == 4


def test_add_frames_from_videos__embeds(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    videos_dir = tmp_path / "videos"
    create_video_file(output_path=videos_dir / "clip.mp4", width=64, height=64, num_frames=4, fps=2)

    dataset = ImageDataset.create(name="test_dataset")
    dataset.add_frames_from_videos(
        videos_path=videos_dir, extract_dir=tmp_path / "frames", fps=None, embed=True
    )

    samples = dataset.query().to_list()
    assert samples
    assert all(len(sample.sample_table.embeddings) == 1 for sample in samples)
