from __future__ import annotations

from pathlib import Path

from pytest_mock import MockerFixture

from lightly_studio.export import export_artifact


def test_remove_export_artifact(tmp_path: Path) -> None:
    export_path = tmp_path / "coco.json"
    export_path.write_text("{}")

    export_artifact.remove_export_artifact(export_path=str(export_path))

    assert not export_path.exists()


def test_remove_export_artifact__unlink_fails(tmp_path: Path, mocker: MockerFixture) -> None:
    export_path = tmp_path / "coco.json"
    export_path.write_text("{}")
    mocker.patch.object(Path, "unlink", side_effect=PermissionError("read-only"))

    export_artifact.remove_export_artifact(export_path=str(export_path))

    assert export_path.exists()
