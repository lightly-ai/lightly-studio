from __future__ import annotations

import json
from pathlib import Path

import pytest

from prepare_release import ci_gate, cli
from prepare_release.errors import PrepareReleaseError


def _api_run(
    name: str,
    status: str = "completed",
    conclusion: str | None = "success",
    started_at: str = "2026-08-21T10:00:00Z",
    run_id: int = 1,
) -> dict[str, object]:
    return {
        "id": run_id,
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "started_at": started_at,
        "html_url": f"https://github.com/lightly-ai/lightly-studio/runs/{run_id}",
    }


def test_parse_check_runs__single_page():
    runs = ci_gate.parse_check_runs({"check_runs": [_api_run("CI Success Check")]})

    assert runs == [
        ci_gate.CheckRun(
            name="CI Success Check",
            status="completed",
            conclusion="success",
            url="https://github.com/lightly-ai/lightly-studio/runs/1",
            started_at="2026-08-21T10:00:00Z",
            run_id=1,
        )
    ]


def test_parse_check_runs__slurped_pages():
    payload = [
        {"check_runs": [_api_run("CI Success Check", run_id=1)]},
        {"check_runs": [_api_run("End2End Success Check", run_id=2)]},
    ]

    runs = ci_gate.parse_check_runs(payload)

    assert [run.name for run in runs] == ["CI Success Check", "End2End Success Check"]


def test_parse_check_runs__running_run_has_no_conclusion():
    payload = {"check_runs": [_api_run("CI Success Check", status="in_progress", conclusion=None)]}

    runs = ci_gate.parse_check_runs(payload)

    assert runs[0].conclusion == ""


def test_evaluate_check_runs__all_green():
    runs = ci_gate.parse_check_runs(
        {
            "check_runs": [
                _api_run("CI Success Check", run_id=1),
                _api_run("End2End Success Check", run_id=2),
            ]
        }
    )

    verdicts = ci_gate.evaluate_check_runs(runs)

    assert [verdict.passed for verdict in verdicts] == [True, True]


def test_evaluate_check_runs__failed_check_is_named():
    runs = ci_gate.parse_check_runs(
        {
            "check_runs": [
                _api_run("CI Success Check", run_id=1),
                _api_run("End2End Success Check", conclusion="failure", run_id=2),
            ]
        }
    )

    verdicts = ci_gate.evaluate_check_runs(runs)

    assert verdicts[0].passed
    assert not verdicts[1].passed
    assert verdicts[1].name == "End2End Success Check"
    assert "failure" in verdicts[1].detail
    assert verdicts[1].url == "https://github.com/lightly-ai/lightly-studio/runs/2"


@pytest.mark.parametrize("status", ["queued", "in_progress"])
def test_evaluate_check_runs__still_running_does_not_pass(status: str):
    runs = ci_gate.parse_check_runs(
        {"check_runs": [_api_run("CI Success Check", status=status, conclusion=None)]}
    )

    verdicts = ci_gate.evaluate_check_runs(runs, required=["CI Success Check"])

    assert not verdicts[0].passed
    assert "still" in verdicts[0].detail


# `cancel-in-progress: true` and unit_test.yml's path filters make these two real
# outcomes rather than hypotheticals. Neither means anything was tested.
@pytest.mark.parametrize("conclusion", ["cancelled", "skipped", "neutral", "timed_out"])
def test_evaluate_check_runs__non_success_conclusion_does_not_pass(conclusion: str):
    runs = ci_gate.parse_check_runs(
        {"check_runs": [_api_run("CI Success Check", conclusion=conclusion)]}
    )

    verdicts = ci_gate.evaluate_check_runs(runs, required=["CI Success Check"])

    assert not verdicts[0].passed
    assert conclusion in verdicts[0].detail


def test_evaluate_check_runs__missing_check_does_not_pass():
    verdicts = ci_gate.evaluate_check_runs([], required=["CI Success Check"])

    assert not verdicts[0].passed
    assert "never reported" in verdicts[0].detail


def test_evaluate_check_runs__misspelled_requirement_does_not_pass_vacuously():
    runs = ci_gate.parse_check_runs({"check_runs": [_api_run("CI Success Check")]})

    verdicts = ci_gate.evaluate_check_runs(runs, required=["Unit Test"])

    assert not verdicts[0].passed


# Every commit on main carries this check twice - once from the merge-queue run
# and once from the push-to-main run, the latter routinely cancelled by
# `cancel-in-progress: true` and therefore reported as `failure`. The green
# attempt tested this exact tree, so it decides; the red one stays visible.
def test_evaluate_check_runs__one_green_attempt_passes():
    runs = ci_gate.parse_check_runs(
        {
            "check_runs": [
                _api_run("CI Success Check", started_at="2026-08-21T09:00:00Z", run_id=1),
                _api_run(
                    "CI Success Check",
                    conclusion="failure",
                    started_at="2026-08-21T11:00:00Z",
                    run_id=2,
                ),
            ]
        }
    )

    verdicts = ci_gate.evaluate_check_runs(runs, required=["CI Success Check"])

    assert verdicts[0].passed
    assert "1 other attempt(s) did not" in verdicts[0].detail
    assert verdicts[0].url == "https://github.com/lightly-ai/lightly-studio/runs/1"


def test_evaluate_check_runs__no_green_attempt_reports_the_newest():
    runs = ci_gate.parse_check_runs(
        {
            "check_runs": [
                _api_run(
                    "CI Success Check",
                    conclusion="failure",
                    started_at="2026-08-21T09:00:00Z",
                    run_id=1,
                ),
                _api_run(
                    "CI Success Check",
                    status="in_progress",
                    conclusion=None,
                    started_at="2026-08-21T11:00:00Z",
                    run_id=2,
                ),
            ]
        }
    )

    verdicts = ci_gate.evaluate_check_runs(runs, required=["CI Success Check"])

    assert not verdicts[0].passed
    assert "still in progress" in verdicts[0].detail
    assert "none green" in verdicts[0].detail


def test_render_report():
    verdicts = [
        ci_gate.CheckVerdict(name="CI Success Check", passed=True, detail="succeeded", url="url-1"),
        ci_gate.CheckVerdict(
            name="End2End Success Check", passed=False, detail="concluded failure", url="url-2"
        ),
    ]

    report = ci_gate.render_report(verdicts=verdicts, sha="0123abc")

    assert "0123abc" in report
    assert "| CI Success Check | ✅ [succeeded](url-1) |" in report
    assert "| End2End Success Check | ❌ [concluded failure](url-2) |" in report


class TestCheckCiCommand:
    def test_check_ci__green_commit_exits_zero(self, tmp_path: Path):
        check_runs = tmp_path / "check-runs.json"
        check_runs.write_text(
            json.dumps(
                {
                    "check_runs": [
                        _api_run("CI Success Check", run_id=1),
                        _api_run("End2End Success Check", run_id=2),
                    ]
                }
            )
        )
        summary = tmp_path / "summary.md"

        exit_code = cli.main(
            [
                "check-ci",
                "--check-runs",
                str(check_runs),
                "--sha",
                "0123abc",
                "--summary",
                str(summary),
            ]
        )

        assert exit_code == 0
        assert "0123abc" in summary.read_text()

    def test_check_ci__red_commit_exits_one(self, tmp_path: Path):
        check_runs = tmp_path / "check-runs.json"
        check_runs.write_text(
            json.dumps(
                {
                    "check_runs": [
                        _api_run("CI Success Check", run_id=1),
                        _api_run("End2End Success Check", conclusion="failure", run_id=2),
                    ]
                }
            )
        )

        exit_code = cli.main(["check-ci", "--check-runs", str(check_runs), "--sha", "0123abc"])

        assert exit_code == 1

    def test_check_ci__commit_without_any_checks_exits_one(self, tmp_path: Path):
        check_runs = tmp_path / "check-runs.json"
        check_runs.write_text(json.dumps({"check_runs": []}))

        exit_code = cli.main(["check-ci", "--check-runs", str(check_runs), "--sha", "0123abc"])

        assert exit_code == 1


def test_parse_check_runs__unreadable_payload_is_refused():
    with pytest.raises(PrepareReleaseError):
        ci_gate.parse_check_runs({"message": "No commit found for SHA"})


# An aggregate job gets no check run until the jobs it waits on are done, so a
# commit whose CI is mid-flight has no run under the required name yet.
def test_evaluate_check_runs__missing_check_while_ci_is_running():
    runs = ci_gate.parse_check_runs(
        {"check_runs": [_api_run("Backend (3.9, DuckDB)", status="in_progress", conclusion=None)]}
    )

    verdicts = ci_gate.evaluate_check_runs(runs, required=["CI Success Check"])

    assert not verdicts[0].passed
    assert "1 check(s) on this commit are still running" in verdicts[0].detail
