from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from lightly_studio.export import export_artifact


def test_remove_export_artifact(tmp_path: Path, mocker: MockerFixture) -> None:
    mocker.patch.object(tempfile, "gettempdir", return_value=str(tmp_path))
    export_path = tmp_path / "coco.json"
    export_path.write_text("{}")

    export_artifact.remove_export_artifact(export_path=str(export_path))

    assert not export_path.exists()


def test_remove_export_artifact__unlink_fails(tmp_path: Path, mocker: MockerFixture) -> None:
    mocker.patch.object(tempfile, "gettempdir", return_value=str(tmp_path))
    export_path = tmp_path / "coco.json"
    export_path.write_text("{}")
    unlink = mocker.patch.object(Path, "unlink", side_effect=PermissionError("read-only"))

    export_artifact.remove_export_artifact(export_path=str(export_path))

    unlink.assert_called_once_with(missing_ok=True)
    assert export_path.exists()


def test_remove_export_artifact__resolve_fails(tmp_path: Path, mocker: MockerFixture) -> None:
    export_path = tmp_path / "coco.json"
    export_path.write_text("{}")
    mocker.patch.object(Path, "resolve", side_effect=RuntimeError("Symlink loop"))

    export_artifact.remove_export_artifact(export_path=str(export_path))

    assert export_path.exists()


def test_remove_export_artifact__rmtree_fails(
    tmp_path: Path, mocker: MockerFixture, caplog: pytest.LogCaptureFixture
) -> None:
    export_dir = tmp_path / "yolo"
    export_dir.mkdir()
    mocker.patch.object(tempfile, "gettempdir", return_value=str(tmp_path))
    rmtree = mocker.patch.object(shutil, "rmtree")

    with caplog.at_level(logging.WARNING):
        export_artifact.remove_export_artifact(export_path=str(export_dir))

    rmtree.assert_called_once_with(export_dir.resolve(), ignore_errors=True)
    assert f"Could not remove export artifact: {export_dir}" in caplog.text


def test_remove_export_artifact__is_dir_fails(tmp_path: Path, mocker: MockerFixture) -> None:
    export_dir = tmp_path / "yolo"
    export_dir.mkdir()
    mocker.patch.object(tempfile, "gettempdir", return_value=str(tmp_path))
    mocker.patch.object(Path, "is_dir", side_effect=PermissionError("no search permission"))

    export_artifact.remove_export_artifact(export_path=str(export_dir))

    assert export_dir.exists()


def test_remove_export_artifact__outside_temp_dir(
    tmp_path: Path, mocker: MockerFixture, caplog: pytest.LogCaptureFixture
) -> None:
    # The fake temp directory does not contain the export artifact below.
    mocker.patch.object(tempfile, "gettempdir", return_value=str(tmp_path / "temp"))
    export_path = tmp_path / "outside" / "coco.json"
    export_path.parent.mkdir()
    export_path.write_text("{}")

    with caplog.at_level(logging.WARNING):
        export_artifact.remove_export_artifact(export_path=str(export_path))

    assert f"Skipping export artifact outside the temp directory: {export_path}" in caplog.text
    assert export_path.exists()


def test_remove_export_artifact__temp_dir_itself(
    tmp_path: Path, mocker: MockerFixture, caplog: pytest.LogCaptureFixture
) -> None:
    mocker.patch.object(tempfile, "gettempdir", return_value=str(tmp_path))

    with caplog.at_level(logging.WARNING):
        export_artifact.remove_export_artifact(export_path=str(tmp_path))

    assert f"Skipping export artifact that is the temp directory itself: {tmp_path}" in caplog.text
    assert tmp_path.exists()
