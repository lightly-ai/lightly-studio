from __future__ import annotations

import pytest

from prepare_release import ci_gate
from prepare_release.errors import PrepareReleaseError

AGGREGATE_CHECKS = ["CI Success Check", "End2End Success Check"]


def _branch_rules(*contexts: str) -> list[dict[str, object]]:
    return [
        {"type": "pull_request", "parameters": {}},
        {
            "type": "required_status_checks",
            "parameters": {
                "required_status_checks": [
                    {"context": context, "integration_id": 15368} for context in contexts
                ]
            },
        },
    ]


def _api_run(
    name: str,
    status: str = "completed",
    conclusion: str | None = "success",
    url: str = "https://github.com/lightly-ai/lightly-studio/runs/1",
) -> dict[str, object]:
    return {"name": name, "status": status, "conclusion": conclusion, "html_url": url}


def test_parse_required_checks():
    assert ci_gate.parse_required_checks(_branch_rules(*AGGREGATE_CHECKS)) == AGGREGATE_CHECKS


def test_parse_required_checks__no_required_checks_is_refused():
    with pytest.raises(PrepareReleaseError):
        ci_gate.parse_required_checks(_branch_rules())


def test_parse_required_checks__ruleset_without_the_rule_is_refused():
    with pytest.raises(PrepareReleaseError):
        ci_gate.parse_required_checks([{"type": "pull_request", "parameters": {}}])


def test_parse_required_checks__unreadable_payload_is_refused():
    with pytest.raises(PrepareReleaseError):
        ci_gate.parse_required_checks({"message": "Not Found"})


def test_parse_check_runs():
    runs = ci_gate.parse_check_runs({"check_runs": [_api_run("CI Success Check")]})

    assert runs == [
        ci_gate.CheckRun(
            name="CI Success Check",
            status="completed",
            conclusion="success",
            url="https://github.com/lightly-ai/lightly-studio/runs/1",
        )
    ]


def test_parse_check_runs__slurped_pages():
    payload = [
        {"check_runs": [_api_run("CI Success Check")]},
        {"check_runs": [_api_run("End2End Success Check")]},
    ]

    runs = ci_gate.parse_check_runs(payload)

    assert [run.name for run in runs] == ["CI Success Check", "End2End Success Check"]


def test_parse_check_runs__running_run_has_no_conclusion():
    payload = {"check_runs": [_api_run("CI Success Check", status="in_progress", conclusion=None)]}

    runs = ci_gate.parse_check_runs(payload)

    assert runs[0].conclusion == ""


def test_parse_check_runs__unreadable_payload_is_refused():
    with pytest.raises(PrepareReleaseError):
        ci_gate.parse_check_runs({"message": "Not Found"})


def test_evaluate_check_runs__all_green():
    runs = ci_gate.parse_check_runs(
        {
            "check_runs": [
                _api_run("CI Success Check"),
                _api_run("End2End Success Check"),
            ]
        }
    )

    verdicts = ci_gate.evaluate_check_runs(runs, required=AGGREGATE_CHECKS)

    assert [verdict.passed for verdict in verdicts] == [True, True]


def test_evaluate_check_runs__failed_check_is_named():
    runs = ci_gate.parse_check_runs(
        {
            "check_runs": [
                _api_run("CI Success Check"),
                _api_run("End2End Success Check", conclusion="failure", url="run-2"),
            ]
        }
    )

    verdicts = ci_gate.evaluate_check_runs(runs, required=AGGREGATE_CHECKS)

    assert verdicts[0].passed
    assert not verdicts[1].passed
    assert verdicts[1].name == "End2End Success Check"
    assert "failure" in verdicts[1].detail
    assert verdicts[1].url == "run-2"


@pytest.mark.parametrize("status", ["queued", "in_progress"])
def test_evaluate_check_runs__still_running_does_not_pass(status: str):
    runs = ci_gate.parse_check_runs(
        {"check_runs": [_api_run("CI Success Check", status=status, conclusion=None)]}
    )

    verdicts = ci_gate.evaluate_check_runs(runs, required=["CI Success Check"])

    assert not verdicts[0].passed
    assert "still" in verdicts[0].detail


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


# An aggregate job gets no check run until the jobs it waits on finish.
def test_evaluate_check_runs__missing_check_while_ci_is_running():
    runs = ci_gate.parse_check_runs(
        {"check_runs": [_api_run("Backend (3.9, DuckDB)", status="in_progress", conclusion=None)]}
    )

    verdicts = ci_gate.evaluate_check_runs(runs, required=["CI Success Check"])

    assert not verdicts[0].passed
    assert "still running" in verdicts[0].detail


def test_evaluate_check_runs__misspelled_requirement_does_not_pass_vacuously():
    runs = ci_gate.parse_check_runs({"check_runs": [_api_run("CI Success Check")]})

    verdicts = ci_gate.evaluate_check_runs(runs, required=["Unit Test"])

    assert not verdicts[0].passed


# Every commit on main carries each check twice, and the push-to-main attempt is
# routinely cancelled, which reports as `failure`.
def test_evaluate_check_runs__one_green_attempt_passes():
    runs = ci_gate.parse_check_runs(
        {
            "check_runs": [
                _api_run("CI Success Check", conclusion="failure", url="red"),
                _api_run("CI Success Check", url="green"),
            ]
        }
    )

    verdicts = ci_gate.evaluate_check_runs(runs, required=["CI Success Check"])

    assert verdicts[0].passed
    assert "1 other attempt(s) did not" in verdicts[0].detail
    assert verdicts[0].url == "green"


def test_evaluate_check_runs__no_green_attempt_reports_every_outcome():
    runs = ci_gate.parse_check_runs(
        {
            "check_runs": [
                _api_run("CI Success Check", conclusion="failure"),
                _api_run("CI Success Check", conclusion="failure"),
                _api_run("CI Success Check", status="in_progress", conclusion=None),
            ]
        }
    )

    verdicts = ci_gate.evaluate_check_runs(runs, required=["CI Success Check"])

    assert not verdicts[0].passed
    assert verdicts[0].detail == "did not succeed: failure, failure, still in progress"


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
