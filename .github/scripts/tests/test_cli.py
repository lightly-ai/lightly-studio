from pathlib import Path

import pytest

from prepare_release import changelog, cli

SAMPLE_PYPROJECT = """\
[project]
name = "lightly-studio"
version = "1.0.5"
description = "..."

dependencies = [
    "labelformat>=0.1.17",
]
"""

SAMPLE_CHANGELOG = """\
# Changelog

## [Unreleased]

### Added

- Added thing one.

### Changed

### Deprecated

### Removed

### Fixed

### Security
"""

SAMPLE_LOCK = """\
version = 1
revision = 2

[[package]]
name = "lightly-studio"
version = "1.0.5"
source = { editable = "." }
"""


def test_main__unknown_command_exits_nonzero():
    with pytest.raises(SystemExit):
        cli.main(["suggest-bump", "--changelog", "CHANGELOG.md"])


def test_main__check_labelformat_pin__passes(tmp_path: Path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(SAMPLE_PYPROJECT)
    assert cli.main(["check-labelformat-pin", "--pyproject", str(pyproject)]) == 0


def test_main__check_labelformat_pin__git_sha_fails(tmp_path: Path, capsys: pytest.CaptureFixture):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        SAMPLE_PYPROJECT.replace(
            '"labelformat>=0.1.17"',
            '"labelformat @ git+https://github.com/lightly-ai/labelformat.git@325a20b"',
        )
    )
    assert cli.main(["check-labelformat-pin", "--pyproject", str(pyproject)]) == 1
    assert "git sha" in capsys.readouterr().err


def test_main__promote_changelog__writes_file(tmp_path: Path):
    changelog_file = tmp_path / "CHANGELOG.md"
    changelog_file.write_text(SAMPLE_CHANGELOG)
    assert (
        cli.main(
            [
                "promote-changelog",
                "--changelog",
                str(changelog_file),
                "--version",
                "1.1.0",
                "--date",
                "2026-08-25",
            ]
        )
        == 0
    )
    promoted = changelog_file.read_text()
    assert "## \\[1.1.0\\] - 2026-08-25" in promoted
    assert "Added thing one" in promoted


def test_main__assert_lock_diff__narrow_diff_passes(tmp_path: Path):
    before = tmp_path / "before.lock"
    after = tmp_path / "after.lock"
    before.write_text(SAMPLE_LOCK)
    after.write_text(SAMPLE_LOCK.replace('version = "1.0.5"', 'version = "1.0.6"'))
    assert (
        cli.main(
            [
                "assert-lock-diff",
                "--before",
                str(before),
                "--after",
                str(after),
                "--package",
                "lightly-studio",
            ]
        )
        == 0
    )


def test_main__assert_lock_diff__wide_diff_fails(tmp_path: Path, capsys: pytest.CaptureFixture):
    before = tmp_path / "before.lock"
    after = tmp_path / "after.lock"
    before.write_text(SAMPLE_LOCK)
    after.write_text(SAMPLE_LOCK.replace('source = { editable = "." }', 'source = { path = "." }'))
    assert (
        cli.main(
            [
                "assert-lock-diff",
                "--before",
                str(before),
                "--after",
                str(after),
                "--package",
                "lightly-studio",
            ]
        )
        == 1
    )
    assert "more than its version line" in capsys.readouterr().err


def test_main__render_pr_body__writes_file(tmp_path: Path):
    changelog_file = tmp_path / "CHANGELOG.md"
    output = tmp_path / "pr_body.md"
    promoted = changelog.promote_changelog(
        changelog_text=SAMPLE_CHANGELOG, version="1.1.0", date="2026-08-25"
    )
    changelog_file.write_text(promoted)
    assert (
        cli.main(
            [
                "render-pr-body",
                "--changelog",
                str(changelog_file),
                "--version",
                "1.1.0",
                "--package",
                "lightly-studio",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    body = output.read_text()
    assert "Added thing one" in body


def test_main__package_config(capsys: pytest.CaptureFixture):
    assert cli.main(["package-config", "--package", "lightly-studio"]) == 0
    assert "pyproject=lightly_studio/pyproject.toml\n" in capsys.readouterr().out


def test_main__package_config__by_tag(capsys: pytest.CaptureFixture):
    assert cli.main(["package-config", "--tag", "lightly-studio-embed/v0.1.1"]) == 0
    assert "distribution=lightly-studio-embed\n" in capsys.readouterr().out


def test_main__package_config__unknown_package_exits_nonzero(capsys: pytest.CaptureFixture):
    assert cli.main(["package-config", "--package", "lightly-train"]) == 1
    assert "unknown package" in capsys.readouterr().err


def test_main__package_config__requires_a_selector():
    with pytest.raises(SystemExit):
        cli.main(["package-config"])


def test_main__list_packages(capsys: pytest.CaptureFixture):
    assert cli.main(["list-packages"]) == 0
    assert capsys.readouterr().out == (
        "lightly-studio lightly_studio/pyproject.toml\n"
        "lightly-studio-embed lightly_studio_embed/pyproject.toml\n"
    )


def test_main__check_wheel_dependencies__no_wheel_exits_nonzero(
    tmp_path: Path, capsys: pytest.CaptureFixture
):
    assert (
        cli.main(
            [
                "check-wheel-dependencies",
                "--package",
                "lightly-studio-embed",
                "--dist",
                str(tmp_path),
            ]
        )
        == 1
    )
    assert "expected exactly one wheel" in capsys.readouterr().err
