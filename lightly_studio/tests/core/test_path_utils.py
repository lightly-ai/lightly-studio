import posixpath
from pathlib import Path

import pytest

from lightly_studio.core import path_utils


def test_normalize_path_root__local_path_is_posix() -> None:
    # On Windows, `str(Path(...).absolute())` returns backslashes which, when
    # joined with posix-separated labelformat filenames via `posixpath.join`,
    # produce mixed-separator strings that fail to match ingested paths.
    # The normalized path must therefore be in posix form.
    result = path_utils.normalize_path_root(Path("some") / "images")

    assert "\\" not in result
    assert result.endswith("some/images")
    assert Path(result).is_absolute()


def test_normalize_path_root__joins_cleanly_with_posix_filename() -> None:
    root = path_utils.normalize_path_root(Path("data") / "coco")
    joined = posixpath.join(root, "images/0001.jpg")

    assert "\\" not in joined
    assert joined.endswith("data/coco/images/0001.jpg")


def test_normalize_path_root__preserves_remote_protocol() -> None:
    result = path_utils.normalize_path_root("s3://bucket/path")

    assert result == "s3://bucket/path"


def test_normalize_path_root__dot_prefixed_path_is_resolved_relative_to_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    result = path_utils.normalize_path_root("./images/0001.jpg")

    assert result == (tmp_path / "images/0001.jpg").as_posix()


def test_normalize_path_root__unprefixed_path_is_resolved_relative_to_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    result = path_utils.normalize_path_root("images/0001.jpg")

    assert result == (tmp_path / "images/0001.jpg").as_posix()


def test_normalize_path_root__absolute_path_is_left_unchanged(tmp_path: Path) -> None:
    absolute_path = tmp_path / "images" / "0001.jpg"

    result = path_utils.normalize_path_root(str(absolute_path))

    assert result == absolute_path.as_posix()
