from __future__ import annotations

import subprocess
from importlib import metadata
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from lightly_studio import export_version


@pytest.fixture
def git_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Create a git repository with two commits and change to it."""
    monkeypatch.chdir(tmp_path)
    _git("init", "--quiet")
    _git("commit", "--quiet", "--allow-empty", "--message", "first")
    _git("commit", "--quiet", "--allow-empty", "--message", "second")


@pytest.mark.usefixtures("git_repo")
def test_get_version_info__annotated_tag(mocker: MockerFixture) -> None:
    mocker.patch.object(metadata, "version", return_value="1.2.3")
    _git("tag", "--annotate", "v1.2.3", "--message", "Release v1.2.3")

    version_info = export_version.get_version_info()

    assert version_info["version"] == "1.2.3"
    assert version_info["git_sha"] == _git("rev-parse", "--short", "HEAD")
    assert version_info["is_tagged_commit"] is True


@pytest.mark.usefixtures("git_repo")
def test_get_version_info__lightweight_tag(mocker: MockerFixture) -> None:
    mocker.patch.object(metadata, "version", return_value="1.2.3")
    _git("tag", "v1.2.3")

    assert export_version.get_version_info()["is_tagged_commit"] is True


@pytest.mark.usefixtures("git_repo")
def test_get_version_info__tag_on_other_commit(mocker: MockerFixture) -> None:
    mocker.patch.object(metadata, "version", return_value="1.2.3")
    _git("tag", "--annotate", "v1.2.3", "HEAD~1", "--message", "Release v1.2.3")

    assert export_version.get_version_info()["is_tagged_commit"] is False


@pytest.mark.usefixtures("git_repo")
def test_get_version_info__no_tag(mocker: MockerFixture) -> None:
    mocker.patch.object(metadata, "version", return_value="1.2.3")
    _git("tag", "--annotate", "v1.2.2", "--message", "Release v1.2.2")

    assert export_version.get_version_info()["is_tagged_commit"] is False


def _git(*args: str) -> str:
    return subprocess.check_output(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "-c",
            "tag.gpgSign=false",
            "-c",
            "commit.gpgSign=false",
            *args,
        ],
        text=True,
    ).strip()
