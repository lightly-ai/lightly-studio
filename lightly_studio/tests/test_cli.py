from __future__ import annotations

import re
from collections.abc import Generator
from pathlib import Path

import pytest
from click.testing import CliRunner
from pytest_mock import MockerFixture

import lightly_studio
from lightly_studio import cli, db_manager


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
