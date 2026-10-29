from __future__ import annotations

from pathlib import Path

import fsspec

from lightly_studio.export import image_files


def test_relative_image_paths() -> None:
    assert image_files.relative_image_paths(
        paths=["s3://bucket/data/cam_a/img.jpg", "s3://bucket/data/cam_b/img.jpg"]
    ) == ["cam_a/img.jpg", "cam_b/img.jpg"]


def test_relative_image_paths__same_folder() -> None:
    assert image_files.relative_image_paths(paths=["/data/a.jpg", "/data/b.jpg"]) == [
        "a.jpg",
        "b.jpg",
    ]


def test_relative_image_paths__mixed_storage_stays_relative() -> None:
    # Local and remote paths share no folder; an absolute result would overwrite the source.
    assert image_files.relative_image_paths(
        paths=["/data/a/x.jpg", "s3://bucket/y.jpg", "C:\\imgs\\z.jpg"]
    ) == ["data/a/x.jpg", "bucket/y.jpg", "imgs/z.jpg"]


def test_relative_image_paths__nested_folder() -> None:
    assert image_files.relative_image_paths(paths=["/data/a.jpg", "/data/sub/b.jpg"]) == [
        "a.jpg",
        "sub/b.jpg",
    ]


def test_relative_image_paths__single_path() -> None:
    assert image_files.relative_image_paths(paths=["/data/cam_a/img.jpg"]) == ["img.jpg"]


def test_relative_image_paths__empty() -> None:
    assert image_files.relative_image_paths(paths=[]) == []


def test_copy_images(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    source.write_bytes(b"image")
    destination = tmp_path / "out" / "sub" / "copy.jpg"

    image_files.copy_images(sources=[str(source)], destinations=[destination])

    assert destination.read_bytes() == b"image"


def test_copy_images__remote_sources_use_workers(tmp_path: Path) -> None:
    sources = [f"memory://bucket/img{i}.jpg" for i in range(3)]
    for i, source in enumerate(sources):
        with fsspec.open(source, "wb") as f:
            f.write(f"image {i}".encode())
    destinations = [tmp_path / f"img{i}.jpg" for i in range(3)]

    image_files.copy_images(sources=sources, destinations=destinations)

    assert [d.read_bytes() for d in destinations] == [b"image 0", b"image 1", b"image 2"]
