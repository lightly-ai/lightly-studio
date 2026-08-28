"""Release gate: the required CI checks must be green on the release commit.

Backs the "Check release CI" composite action
(`.github/actions/check-release-ci/action.yml`), which resolves a ref to a
sha, fetches that commit's check runs and hands them to the `check-ci`
subcommand. Nothing here touches the network, so every rule below is
covered by offline unit tests.

Three decisions are worth spelling out, because getting any of them wrong
turns this into a gate that waves everything through - which is worse than
no gate, since it also removes the manual checking it replaced:

- **The required names are job names, not workflow names.** GitHub names a
  check run after the job that produced it, so "Unit Test" and "End2End
  Test" - the workflow names - match nothing and would pass vacuously.
- **Only `success` passes.** A missing check, a still-running one,
  `cancelled`, `skipped` and `neutral` all block. `cancel-in-progress:
  true` in both test workflows makes `cancelled` routine, and
  unit_test.yml's path filters make `skipped` real; neither is evidence
  that anything was tested.
- **One completed green attempt is enough.** A commit on `main` carries the
  same check twice: once from the merge-queue run and once from the
  push-to-main run. `cancel-in-progress: true` routinely cancels the latter
  when the next merge lands, and a cancelled aggregate job reports
  `failure`, so "the newest attempt wins" would block nearly every commit -
  and a gate that blocks everything gets overridden by habit, which is the
  same loss of vigilance by another route. A completed `success` means this
  exact tree was tested green; any other attempts are reported alongside it
  so a genuine flake stays visible.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from typing import Any

from prepare_release.errors import PrepareReleaseError

# The single aggregate job of each test workflow, and the checks required by
# the branch ruleset. Both run with `if: always()`, so they are reported for
# every commit and never come back `skipped`: the per-job `skipped` results
# that unit_test.yml's path filters produce are resolved inside "CI Success
# Check" itself. Requiring the aggregates rather than the individual jobs is
# therefore what keeps path-filtered commits from stranding the gate.
# This tuple is the single place the required checks are named; workflows
# pass no list of their own.
REQUIRED_CHECKS: tuple[str, ...] = ("CI Success Check", "End2End Success Check")

_COMPLETED = "completed"
_SUCCESS = "success"


@dataclasses.dataclass(frozen=True)
class CheckRun:
    """One check run GitHub reports for a commit.

    Attributes:
        name: Name of the job that produced the run.
        status: `queued`, `in_progress` or `completed`.
        conclusion: `success`, `failure`, `cancelled`, `skipped`, ...; empty
            while the run is not completed.
        url: Link to the run on GitHub.
        started_at: ISO 8601 start timestamp, used to find the latest attempt.
        run_id: Check run id, tie-breaker for attempts started in the same second.
    """

    name: str
    status: str
    conclusion: str
    url: str
    started_at: str
    run_id: int


@dataclasses.dataclass(frozen=True)
class CheckVerdict:
    """The gate's reading of one required check.

    Attributes:
        name: The required check name.
        passed: Whether the check is green on the commit.
        detail: Why, phrased to follow the check name in a sentence.
        url: Link to the run that decided it, empty when there is none.
    """

    name: str
    passed: bool
    detail: str
    url: str


def parse_check_runs(payload: Any) -> list[CheckRun]:
    """Flattens the JSON of `gh api repos/.../commits/<sha>/check-runs`.

    Args:
        payload: Either one API response object, or the list of page objects
            that `gh api --paginate --slurp` produces.

    Returns:
        Every check run in the payload, in the order the API returned them.

    Raises:
        PrepareReleaseError: The payload is not a check-runs response, e.g.
            because the API call errored and its output was captured anyway.
    """
    pages = payload if isinstance(payload, list) else [payload]
    if not all(isinstance(page, dict) and "check_runs" in page for page in pages):
        raise PrepareReleaseError(
            "Not a check-runs API response; the gate cannot tell a red commit from an "
            "unreadable one, so it refuses to pass."
        )
    return [
        CheckRun(
            name=run["name"],
            status=run["status"],
            conclusion=run["conclusion"] or "",
            url=run.get("html_url") or "",
            started_at=run.get("started_at") or "",
            run_id=run["id"],
        )
        for page in pages
        for run in page["check_runs"]
    ]


def evaluate_check_runs(
    check_runs: Sequence[CheckRun], required: Sequence[str] = REQUIRED_CHECKS
) -> list[CheckVerdict]:
    """Judges each required check against the runs reported for one commit.

    Args:
        check_runs: Every check run on the commit, from `parse_check_runs`.
        required: Names that must be green; defaults to `REQUIRED_CHECKS`.

    Returns:
        One verdict per required name, in the order given.
    """
    return [
        _verdict(name=name, runs=[run for run in check_runs if run.name == name])
        for name in required
    ]


def render_report(verdicts: Sequence[CheckVerdict], sha: str) -> str:
    """Renders the verdicts as a markdown table for the job summary."""
    lines = [
        f"### Release CI gate for `{sha}`",
        "",
        "| Required check | Result |",
        "| --- | --- |",
    ]
    for verdict in verdicts:
        mark = "✅" if verdict.passed else "❌"
        detail = f"[{verdict.detail}]({verdict.url})" if verdict.url else verdict.detail
        lines.append(f"| {verdict.name} | {mark} {detail} |")
    return "\n".join(lines) + "\n"


def _verdict(name: str, runs: Sequence[CheckRun]) -> CheckVerdict:
    """Judges one required check from every attempt reported under its name."""
    if not runs:
        return CheckVerdict(
            name=name, passed=False, detail="was never reported on this commit", url=""
        )

    successes = [run for run in runs if run.status == _COMPLETED and run.conclusion == _SUCCESS]
    if successes:
        latest = max(successes, key=_attempt_order)
        return CheckVerdict(
            name=name,
            passed=True,
            detail=_succeeded_detail(len(runs) - len(successes)),
            url=latest.url,
        )

    latest = max(runs, key=_attempt_order)
    if latest.status != _COMPLETED:
        detail = f"is still {latest.status.replace('_', ' ')}"
    else:
        detail = f"concluded {latest.conclusion or 'without a conclusion'}"
    return CheckVerdict(
        name=name, passed=False, detail=_of_attempts(detail, len(runs)), url=latest.url
    )


def _attempt_order(run: CheckRun) -> tuple[str, int]:
    """Orders attempts by start time, with the run id as a tie-breaker."""
    return (run.started_at, run.run_id)


def _succeeded_detail(not_green: int) -> str:
    """Describes a green check, flagging any sibling attempt that was not green."""
    if not_green == 0:
        return "succeeded"
    return f"succeeded, but {not_green} other attempt(s) did not"


def _of_attempts(detail: str, attempts: int) -> str:
    """Appends the attempt count when more than one attempt was reported."""
    if attempts == 1:
        return detail
    return f"{detail} (newest of {attempts} attempts, none green)"
