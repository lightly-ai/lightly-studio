from __future__ import annotations

import re

from click.testing import CliRunner
from pytest_mock import MockerFixture

import lightly_studio
from lightly_studio import cli


def test_main__version_option() -> None:
    runner = CliRunner()
    result = runner.invoke(cli=cli.main, args=["--version"])
    assert result.exit_code == 0
    assert re.search(r"lightly-studio, version \d+\.\d+\.\d+", result.output)


def test_gui(mocker: MockerFixture) -> None:
    mock_start_gui = mocker.patch.object(lightly_studio, "start_gui")
    runner = CliRunner()
    result = runner.invoke(cli=cli.main, args=["gui"])
    assert result.exit_code == 0
    mock_start_gui.assert_called_once()
