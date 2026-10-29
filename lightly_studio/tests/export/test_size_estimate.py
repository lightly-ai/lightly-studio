from __future__ import annotations

from pathlib import Path

from lightly_studio.export import size_estimate


def _write(tmp_path: Path, sizes: list[int]) -> list[str]:
    paths = []
    for index, size in enumerate(sizes):
        path = tmp_path / f"img{index}.jpg"
        path.write_bytes(b"x" * size)
        paths.append(str(path))
    return paths


def test_estimate_total_bytes__all_files_sampled(tmp_path: Path) -> None:
    paths = _write(tmp_path, sizes=[100, 200, 300, 400])

    assert size_estimate.estimate_total_bytes(file_paths=paths, sample_size=4) == 1000


def test_estimate_total_bytes__scales_an_evenly_spaced_sample(tmp_path: Path) -> None:
    # Samples img0 and img2: average 200 bytes, times 4 files.
    paths = _write(tmp_path, sizes=[100, 200, 300, 400])

    assert size_estimate.estimate_total_bytes(file_paths=paths, sample_size=2) == 800


def test_estimate_total_bytes__skips_missing_files(tmp_path: Path) -> None:
    paths = [*_write(tmp_path, sizes=[100]), str(tmp_path / "missing.jpg")]

    assert size_estimate.estimate_total_bytes(file_paths=paths, sample_size=2) == 200


def test_estimate_total_bytes__none_when_nothing_is_readable(tmp_path: Path) -> None:
    assert size_estimate.estimate_total_bytes(file_paths=[str(tmp_path / "a.jpg")]) is None
    assert size_estimate.estimate_total_bytes(file_paths=[]) is None
