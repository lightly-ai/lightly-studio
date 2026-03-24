from __future__ import annotations

from importlib import metadata

from click.testing import CliRunner
from pytest_mock import MockerFixture

from lightly_studio import cli


def test_main__version_option() -> None:
    runner = CliRunner()
    result = runner.invoke(cli=cli.main, args=["--version"])
    assert result.exit_code == 0
    assert metadata.version("lightly-studio") in result.output


def test_main__no_subcommand_prints_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli=cli.main, args=[])
    assert result.exit_code == 0
    assert "LightlyStudio CLI" in result.output


def test_gui(mocker: MockerFixture) -> None:
    mock_start_gui = mocker.patch.object(cli, "start_gui")
    runner = CliRunner()
    result = runner.invoke(cli=cli.main, args=["gui"])
    assert result.exit_code == 0
    mock_start_gui.assert_called_once()
