from __future__ import annotations

from importlib.metadata import version
from unittest.mock import MagicMock

from click.testing import CliRunner

from lightly_studio.cli import main


def test_version_option() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert version("lightly-studio") in result.output


def test_no_subcommand_prints_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, [])
    assert result.exit_code == 0
    assert "LightlyStudio CLI" in result.output


def test_gui_calls_start_gui(monkeypatch: object) -> None:
    mock_start_gui = MagicMock()
    import lightly_studio

    monkeypatch.setattr(lightly_studio, "start_gui", mock_start_gui)  # type: ignore[attr-defined]

    runner = CliRunner()
    result = runner.invoke(main, ["gui"])
    assert result.exit_code == 0
    mock_start_gui.assert_called_once()
