import json
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

SAMPLE_BRANCH_RULES = [
    {
        "type": "required_status_checks",
        "parameters": {
            "required_status_checks": [
                {"context": "CI Success Check"},
                {"context": "End2End Success Check"},
            ]
        },
    }
]

SAMPLE_CHECK_RUN = {
    "name": "CI Success Check",
    "status": "completed",
    "conclusion": "success",
    "html_url": "https://github.com/lightly-ai/lightly-studio/runs/1",
}


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
                "--output",
                str(output),
            ]
        )
        == 0
    )
    body = output.read_text()
    assert "Added thing one" in body


def _check_ci_files(tmp_path: Path, *runs: dict[str, object]) -> tuple[Path, Path]:
    check_runs = tmp_path / "check-runs.json"
    check_runs.write_text(json.dumps({"check_runs": list(runs)}))
    branch_rules = tmp_path / "branch-rules.json"
    branch_rules.write_text(json.dumps(SAMPLE_BRANCH_RULES))
    return check_runs, branch_rules


def _check_ci_argv(check_runs: Path, branch_rules: Path) -> list[str]:
    return [
        "check-ci",
        "--check-runs",
        str(check_runs),
        "--branch-rules",
        str(branch_rules),
        "--sha",
        "0123abc",
    ]


def test_main__check_ci__green_commit_passes(tmp_path: Path):
    check_runs, branch_rules = _check_ci_files(
        tmp_path,
        SAMPLE_CHECK_RUN | {"name": "CI Success Check"},
        SAMPLE_CHECK_RUN | {"name": "End2End Success Check"},
    )
    summary = tmp_path / "summary.md"

    exit_code = cli.main([*_check_ci_argv(check_runs, branch_rules), "--summary", str(summary)])

    assert exit_code == 0
    assert "0123abc" in summary.read_text()


def test_main__check_ci__red_commit_fails(tmp_path: Path):
    check_runs, branch_rules = _check_ci_files(
        tmp_path,
        SAMPLE_CHECK_RUN | {"name": "CI Success Check"},
        SAMPLE_CHECK_RUN | {"name": "End2End Success Check", "conclusion": "failure"},
    )

    exit_code = cli.main(_check_ci_argv(check_runs, branch_rules))

    assert exit_code == 1


# A ruleset that requires nothing must not be read as "everything passes".
def test_main__check_ci__ruleset_without_required_checks_fails(tmp_path: Path):
    check_runs, branch_rules = _check_ci_files(
        tmp_path,
        SAMPLE_CHECK_RUN | {"name": "CI Success Check"},
        SAMPLE_CHECK_RUN | {"name": "End2End Success Check"},
    )
    branch_rules.write_text(json.dumps([{"type": "pull_request", "parameters": {}}]))

    exit_code = cli.main(_check_ci_argv(check_runs, branch_rules))

    assert exit_code == 1
