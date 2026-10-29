import posixpath
from pathlib import Path

import fsspec
import pytest
from pytest_mock import MockerFixture

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


def test_check_input_file(tmp_path: Path) -> None:
    labels_path = tmp_path / "labels.json"
    labels_path.write_text("{}")

    path_utils.check_input_file(path=labels_path, description="labels file", suffix=".json")


def test_check_input_file__remote_file() -> None:
    fs = fsspec.filesystem("memory")
    fs.pipe("/bucket/labels.json", b"{}")

    path_utils.check_input_file(
        path="memory://bucket/labels.json", description="labels file", suffix=".json"
    )


def test_check_input_file__wrong_suffix(tmp_path: Path) -> None:
    labels_path = tmp_path / "labels.txt"
    labels_path.write_text("{}")

    with pytest.raises(ValueError, match=r"The labels file must end with '\.json', got: '.*txt'"):
        path_utils.check_input_file(path=labels_path, description="labels file", suffix=".json")


def test_check_input_file__missing_file(tmp_path: Path) -> None:
    labels_path = tmp_path / "labels.json"

    with pytest.raises(FileNotFoundError, match=f"Labels file not found: '{labels_path}'.$"):
        path_utils.check_input_file(path=labels_path, description="labels file", suffix=".json")


def test_check_input_file__missing_file_with_double_slash() -> None:
    with pytest.raises(FileNotFoundError, match="The path contains '//'"):
        path_utils.check_input_file(
            path="memory://bucket/run//labels.json", description="labels file", suffix=".json"
        )


def test_check_input_file__directory(tmp_path: Path) -> None:
    labels_path = tmp_path / "labels.json"
    labels_path.mkdir()

    with pytest.raises(IsADirectoryError, match="The labels file is a directory, not a file"):
        path_utils.check_input_file(path=labels_path, description="labels file", suffix=".json")


def test_check_input_file__access_error_names_path_and_cause(mocker: MockerFixture) -> None:
    # s3fs.isfile() returns False for this error, but info() raises it.
    fs = mocker.MagicMock()
    fs.info.side_effect = PermissionError("Access Denied")
    mocker.patch.object(fsspec.core, "url_to_fs", return_value=(fs, "bucket/labels.json"))

    with pytest.raises(
        OSError,
        match=(
            r"Could not access the labels file 's3://bucket/labels\.json': "
            r"PermissionError: Access Denied"
        ),
    ):
        path_utils.check_input_file(
            path="s3://bucket/labels.json", description="labels file", suffix=".json"
        )
