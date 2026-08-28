"""Release gate: the required CI checks must be green on the release commit.

Backs the "Check release CI" composite action, which resolves a ref to a sha,
fetches that commit's check runs and hands them to the `check-ci` subcommand.
Nothing here touches the network, so every rule below is unit tested offline.

A gate that waves everything through is worse than no gate, because it also
replaces the manual checking it removed. Hence the three rules: the required
names come from the branch ruleset rather than a copy kept here, which would
drift from it silently; only a completed `success` passes; and one green
attempt is enough, because `cancel-in-progress: true` cancels the
push-to-main attempt of nearly every commit on `main`.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from typing import Any

from prepare_release.errors import PrepareReleaseError

_REQUIRED_STATUS_CHECKS = "required_status_checks"
_COMPLETED = "completed"
_SUCCESS = "success"


@dataclasses.dataclass(frozen=True)
class CheckRun:
    """One check run GitHub reports for a commit, named after the job that produced it.

    Attributes:
        conclusion: Empty while the run has not completed.
    """

    name: str
    status: str
    conclusion: str
    url: str


@dataclasses.dataclass(frozen=True)
class CheckVerdict:
    """The gate's reading of one required check.

    Attributes:
        detail: Why, phrased to follow the check name in a sentence.
        url: The run that decided it, empty when there is none.
    """

    name: str
    passed: bool
    detail: str
    url: str


def parse_required_checks(payload: Any) -> list[str]:
    """Reads the required check names out of `gh api repos/.../rules/branches/<branch>`.

    The branch ruleset is where the team already agreed which checks must pass
    before anything reaches `main`, so the gate asks it rather than keeping a
    second list. Note that check runs are named after jobs, so a hand-written
    list of the workflow names would match nothing and pass everything.

    Raises:
        PrepareReleaseError: The payload is not a rules response, or it names no
            required checks. Requiring nothing would pass every commit, so it is
            refused rather than obeyed.
    """
    if not isinstance(payload, list):
        raise PrepareReleaseError(
            "Not a branch-rules API response; the gate cannot tell which checks are "
            "required, so it refuses to pass."
        )
    contexts = [
        check["context"]
        for rule in payload
        if isinstance(rule, dict) and rule.get("type") == _REQUIRED_STATUS_CHECKS
        for check in rule.get("parameters", {}).get(_REQUIRED_STATUS_CHECKS, [])
    ]
    if not contexts:
        raise PrepareReleaseError(
            "The branch ruleset names no required status checks. Requiring nothing "
            "would pass every commit, so the gate refuses instead. Fix the ruleset "
            "before releasing."
        )
    return contexts


def parse_check_runs(payload: Any) -> list[CheckRun]:
    """Flattens the JSON of `gh api repos/.../commits/<sha>/check-runs`.

    Args:
        payload: One API response object, or the list of pages that
            `gh api --paginate --slurp` produces.

    Raises:
        PrepareReleaseError: The payload is not a check-runs response, so the
            gate cannot tell a red commit from an unreadable one.
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
        )
        for page in pages
        for run in page["check_runs"]
    ]


def evaluate_check_runs(
    check_runs: Sequence[CheckRun], required: Sequence[str]
) -> list[CheckVerdict]:
    """Judges each required check against the runs reported for one commit."""
    ci_running = any(run.status != _COMPLETED for run in check_runs)
    return [
        _verdict(
            name=name,
            runs=[run for run in check_runs if run.name == name],
            ci_running=ci_running,
        )
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


def _verdict(name: str, runs: Sequence[CheckRun], ci_running: bool) -> CheckVerdict:
    """Judges one required check from every attempt reported under its name.

    An aggregate job only gets a check run once the jobs it waits on are done,
    so a commit whose CI is still running (`ci_running`) has no run under this
    name yet - which must not read as "CI never ran".
    """
    if not runs:
        detail = "was never reported on this commit"
        if ci_running:
            detail = "is not reported yet; CI on this commit is still running"
        return CheckVerdict(name=name, passed=False, detail=detail, url="")

    green = [run for run in runs if run.status == _COMPLETED and run.conclusion == _SUCCESS]
    if green:
        not_green = len(runs) - len(green)
        detail = "succeeded"
        if not_green:
            detail = f"succeeded, but {not_green} other attempt(s) did not"
        return CheckVerdict(name=name, passed=True, detail=detail, url=green[0].url)

    outcomes = ", ".join(_outcome(run) for run in runs)
    return CheckVerdict(
        name=name, passed=False, detail=f"did not succeed: {outcomes}", url=runs[0].url
    )


def _outcome(run: CheckRun) -> str:
    """Names what one attempt did: its conclusion, or its status while it has none."""
    if run.status != _COMPLETED:
        return f"still {run.status.replace('_', ' ')}"
    return run.conclusion or "completed without a conclusion"
