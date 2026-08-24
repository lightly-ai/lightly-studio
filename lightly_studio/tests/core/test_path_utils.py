import posixpath
from pathlib import Path

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
