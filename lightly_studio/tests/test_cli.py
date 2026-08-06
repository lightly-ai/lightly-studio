from __future__ import annotations

import json
import re
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from PIL import Image
from pytest_mock import MockerFixture

import lightly_studio
from lightly_studio import cli
from lightly_studio.database import db_manager
from lightly_studio.models.evaluation_run import EvaluationTaskType
from lightly_studio.resolvers import annotation_resolver, evaluation_run_resolver


@pytest.fixture(autouse=True)
def cleanup_db_manager() -> Generator[None, None, None]:
    """Ensure tests do not leak the global database engine."""
    db_manager.close()
    yield
    db_manager.close()


def test_main__version_option() -> None:
    runner = CliRunner()
    result = runner.invoke(cli=cli.main, args=["--version"])
    assert result.exit_code == 0
    assert re.search(r"lightly-studio, version \d+\.\d+\.\d+", result.output)


def test_gui(mocker: MockerFixture) -> None:
    mock_connect = mocker.patch.object(db_manager, "connect")
    mock_start_gui = mocker.patch.object(lightly_studio, "start_gui")
    runner = CliRunner()
    result = runner.invoke(cli=cli.main, args=["gui"])
    assert result.exit_code == 0
    mock_connect.assert_called_once_with(db_file=None, db_url=None, must_exist=True)
    mock_start_gui.assert_called_once_with(host=None, port=None)


def test_gui__with_host_port(mocker: MockerFixture) -> None:
    mock_connect = mocker.patch.object(db_manager, "connect")
    mock_start_gui = mocker.patch.object(lightly_studio, "start_gui")
    runner = CliRunner()
    result = runner.invoke(cli=cli.main, args=["gui", "--host", "0.0.0.0", "--port", "9999"])
    assert result.exit_code == 0
    mock_connect.assert_called_once_with(db_file=None, db_url=None, must_exist=True)
    mock_start_gui.assert_called_once_with(host="0.0.0.0", port=9999)


def test_gui__with_db_file(mocker: MockerFixture) -> None:
    mock_connect = mocker.patch.object(db_manager, "connect")
    mock_start_gui = mocker.patch.object(lightly_studio, "start_gui")
    runner = CliRunner()
    result = runner.invoke(cli=cli.main, args=["gui", "--db-file", "my_duck.db"])
    assert result.exit_code == 0
    mock_connect.assert_called_once_with(db_file="my_duck.db", db_url=None, must_exist=True)
    mock_start_gui.assert_called_once_with(host=None, port=None)


def test_gui__with_db_url(mocker: MockerFixture) -> None:
    mock_connect = mocker.patch.object(db_manager, "connect")
    mock_start_gui = mocker.patch.object(lightly_studio, "start_gui")
    runner = CliRunner()
    result = runner.invoke(cli=cli.main, args=["gui", "--db-url", "postgresql://localhost/mydb"])
    assert result.exit_code == 0
    mock_connect.assert_called_once_with(
        db_file=None, db_url="postgresql://localhost/mydb", must_exist=True
    )
    mock_start_gui.assert_called_once_with(host=None, port=None)


def test_gui__with_db_file_and_db_url(mocker: MockerFixture) -> None:
    mocker.patch.object(db_manager, "connect")
    mocker.patch.object(lightly_studio, "start_gui")
    runner = CliRunner()
    result = runner.invoke(
        cli=cli.main,
        args=["gui", "--db-file", "my_duck.db", "--db-url", "postgresql://localhost/mydb"],
    )
    assert result.exit_code != 0
    assert "mutually exclusive" in result.output


def test_gui__nonexistent_db_file(
    tmp_path: Path,
) -> None:
    db_file = tmp_path / "nonexistent.db"
    runner = CliRunner()
    result = runner.invoke(cli=cli.main, args=["gui", "--db-file", str(db_file)])

    assert result.exit_code != 0
    assert isinstance(result.exception, FileNotFoundError)
    assert f"Database does not exist at duckdb:///{db_file}" in str(result.exception)
    assert not db_file.exists()


def test_gui__with_empty_db_file__complains_about_missing_dataset(
    tmp_path: Path,
) -> None:
    db_file = tmp_path / "empty.db"
    db_manager.connect(db_file=str(db_file), cleanup_existing=True)
    db_manager.close()
    runner = CliRunner()
    result = runner.invoke(cli=cli.main, args=["gui", "--db-file", str(db_file)])

    assert result.exit_code != 0
    assert isinstance(result.exception, ValueError)
    assert "No datasets found" in str(result.exception)


def _mock_demo_dependencies(mocker: MockerFixture) -> tuple[Any, Any, Any, Any]:
    mock_download = mocker.patch.object(
        lightly_studio.utils, "download_example_dataset", return_value="/dataset_examples"
    )
    mock_connect = mocker.patch.object(db_manager, "connect")
    mock_dataset = mocker.MagicMock()
    mock_create = mocker.patch.object(
        lightly_studio.ImageDataset, "create", return_value=mock_dataset
    )
    mock_start_gui = mocker.patch.object(lightly_studio, "start_gui")
    return mock_download, mock_connect, mock_create, mock_start_gui


def test_demo(mocker: MockerFixture) -> None:
    mock_download, mock_connect, mock_create, mock_start_gui = _mock_demo_dependencies(mocker)
    runner = CliRunner()
    result = runner.invoke(cli=cli.main, args=["demo"])
    assert result.exit_code == 0
    mock_download.assert_called_once_with(download_dir="dataset_examples", force_redownload=False)
    mock_connect.assert_called_once_with(db_file="demo.db", cleanup_existing=True)
    mock_create.assert_called_once_with()
    mock_start_gui.assert_called_once_with(port=None)


def test_demo__with_force_download(mocker: MockerFixture) -> None:
    mock_download, mock_connect, _, _ = _mock_demo_dependencies(mocker)
    runner = CliRunner()
    result = runner.invoke(cli=cli.main, args=["demo", "--force-download"])
    assert result.exit_code == 0
    mock_download.assert_called_once_with(download_dir="dataset_examples", force_redownload=True)
    mock_connect.assert_called_once_with(db_file="demo.db", cleanup_existing=True)


def test_demo__with_port(mocker: MockerFixture) -> None:
    _, _, _, mock_start_gui = _mock_demo_dependencies(mocker)
    runner = CliRunner()
    result = runner.invoke(cli=cli.main, args=["demo", "--port", "9999"])
    assert result.exit_code == 0
    mock_start_gui.assert_called_once_with(port=9999)


def _coco_dict_with(file_names: list[str]) -> dict[str, Any]:
    return {
        "images": [
            {"id": i + 1, "file_name": fn, "width": 10, "height": 10}
            for i, fn in enumerate(file_names)
        ],
        "annotations": [
            {
                "id": i + 1,
                "image_id": i + 1,
                "category_id": 1,
                "bbox": [1, 1, 2, 2],
                "area": 4,
                "iscrowd": 0,
            }
            for i in range(len(file_names))
        ],
        "categories": [{"id": 1, "name": "cat"}],
    }


def _build_demo_dataset_dir(root: Path) -> Path:
    """Build a fixture dataset with the same layout as the real demo dataset."""
    dataset_dir = root / "dataset_examples"
    images_dir = dataset_dir / "coco_subset_128_images" / "images"
    images_dir.mkdir(parents=True)
    file_names = [f"image{i}.jpg" for i in range(3)]
    for file_name in file_names:
        Image.new("RGB", (10, 10)).save(images_dir / file_name)
    coco_dir = dataset_dir / "coco_subset_128_images"
    (coco_dir / "instances_train2017.json").write_text(json.dumps(_coco_dict_with(file_names)))
    (coco_dir / "predictions_train2017.json").write_text(json.dumps(_coco_dict_with(file_names)))
    return dataset_dir


def test_demo__runs_real_evaluation_pipeline(
    mocker: MockerFixture, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Loads real images, real COCO annotations, and persists a real evaluation run.

    Runs against its own isolated 'demo.db', without any network access.
    """
    monkeypatch.chdir(tmp_path)
    dataset_dir = _build_demo_dataset_dir(tmp_path)
    mocker.patch.object(
        lightly_studio.utils, "download_example_dataset", return_value=str(dataset_dir)
    )
    mocker.patch.object(lightly_studio, "start_gui")

    runner = CliRunner()
    result = runner.invoke(cli=cli.main, args=["demo"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "demo.db").exists()

    dataset = lightly_studio.ImageDataset.load()
    assert len(dataset.query().to_list()) == 3

    evaluation_runs = evaluation_run_resolver.get_all_by_dataset_id(
        session=dataset.session, dataset_id=dataset.dataset_id
    )
    assert len(evaluation_runs) == 1
    assert evaluation_runs[0].name == "od_evaluation"
    assert evaluation_runs[0].task_type == EvaluationTaskType.OBJECT_DETECTION


def test_demo__second_run_without_force_download_does_not_duplicate_or_crash(
    mocker: MockerFixture, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression test for a bug where demo crashed on a second run.

    Previously demo.db was only wiped for --force-download, so a second run duplicated
    annotations and then crashed with an IntegrityError on the evaluation run insert.
    """
    monkeypatch.chdir(tmp_path)
    dataset_dir = _build_demo_dataset_dir(tmp_path)
    mocker.patch.object(
        lightly_studio.utils, "download_example_dataset", return_value=str(dataset_dir)
    )
    mocker.patch.object(lightly_studio, "start_gui")

    runner = CliRunner()
    assert runner.invoke(cli=cli.main, args=["demo"]).exit_code == 0
    # Each `lightly-studio demo` invocation is normally its own process, starting with no
    # engine set. Close the engine here to reproduce that between the two invokes below.
    db_manager.close()
    result_second = runner.invoke(cli=cli.main, args=["demo"])
    assert result_second.exit_code == 0, result_second.output

    dataset = lightly_studio.ImageDataset.load()
    assert len(dataset.query().to_list()) == 3

    evaluation_runs = evaluation_run_resolver.get_all_by_dataset_id(
        session=dataset.session, dataset_id=dataset.dataset_id
    )
    assert len(evaluation_runs) == 1

    ground_truth = annotation_resolver.get_all_by_collection_name(
        session=dataset.session,
        collection_name="ground_truth",
        parent_collection_id=dataset.collection_id,
    )
    # 3 fixture images x 1 annotation each in _coco_dict_with — must stay at 3, not double to 6.
    assert len(ground_truth.annotations) == 3
