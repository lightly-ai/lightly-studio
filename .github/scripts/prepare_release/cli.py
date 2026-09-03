"""Command-line entry point for the prepare-release tooling.

Backs the "Prepare Release" GitHub Actions workflow
(`.github/workflows/prepare_release.yml`). Each subcommand does one small,
independently testable piece of preparing a release: promoting the
changelog and guarding against a handful of ways that can quietly go
wrong. Reading/bumping/writing the `[project]` version itself is left to
`uv version --bump` directly in the workflow (see version.py's docstring).

Usage:
    python -m prepare_release promote-changelog --changelog CHANGELOG.md \
        --version 1.0.6 --date 2026-08-21
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from prepare_release import changelog, ci_gate, lock, pr_body, version
from prepare_release.errors import PrepareReleaseError

CHECK_LABELFORMAT_PIN = "check-labelformat-pin"
PROMOTE_CHANGELOG = "promote-changelog"
ASSERT_LOCK_DIFF = "assert-lock-diff"
RENDER_PR_BODY = "render-pr-body"
CHECK_CI = "check-ci"


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: parses `argv`, dispatches to the matching subcommand."""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_pin = subparsers.add_parser(
        CHECK_LABELFORMAT_PIN, help="fail if labelformat is pinned by git sha"
    )
    check_pin.add_argument("--pyproject", type=Path, required=True)

    promote = subparsers.add_parser(
        PROMOTE_CHANGELOG, help="promote [Unreleased] to a released version block"
    )
    promote.add_argument("--changelog", type=Path, required=True)
    promote.add_argument("--version", required=True)
    promote.add_argument("--date", required=True, help="YYYY-MM-DD")

    lock_diff = subparsers.add_parser(
        ASSERT_LOCK_DIFF, help="fail if uv sync changed more than the version bump"
    )
    lock_diff.add_argument("--before", type=Path, required=True)
    lock_diff.add_argument("--after", type=Path, required=True)
    lock_diff.add_argument("--package", required=True)

    pr_body_parser = subparsers.add_parser(RENDER_PR_BODY, help="assemble the release PR body")
    pr_body_parser.add_argument("--changelog", type=Path, required=True)
    pr_body_parser.add_argument("--version", required=True)
    pr_body_parser.add_argument("--output", type=Path, required=True)

    check_ci = subparsers.add_parser(
        CHECK_CI, help="fail unless the required CI checks are green on a commit"
    )
    check_ci.add_argument(
        "--check-runs",
        type=Path,
        required=True,
        help="JSON of `gh api repos/<repo>/commits/<sha>/check-runs`",
    )
    check_ci.add_argument("--sha", required=True, help="the commit the runs belong to")
    check_ci.add_argument(
        "--branch-rules",
        type=Path,
        required=True,
        help="JSON of `gh api repos/<repo>/rules/branches/<branch>`, naming the required checks",
    )
    check_ci.add_argument(
        "--summary", type=Path, help="file the markdown report is appended to, e.g. the job summary"
    )

    args = parser.parse_args(argv)

    try:
        return _dispatch(args)
    except PrepareReleaseError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


def _dispatch(args: argparse.Namespace) -> int:
    handlers = {
        CHECK_LABELFORMAT_PIN: _cmd_check_labelformat_pin,
        PROMOTE_CHANGELOG: _cmd_promote_changelog,
        ASSERT_LOCK_DIFF: _cmd_assert_lock_diff,
        RENDER_PR_BODY: _cmd_render_pr_body,
        CHECK_CI: _cmd_check_ci,
    }
    handlers[args.command](args)
    return 0


def _cmd_check_labelformat_pin(args: argparse.Namespace) -> None:
    version.check_labelformat_pin(args.pyproject.read_text())


def _cmd_promote_changelog(args: argparse.Namespace) -> None:
    original = args.changelog.read_text()
    promoted = changelog.promote_changelog(
        changelog_text=original, version=args.version, date=args.date
    )
    changelog.assert_changelog_structure(
        original_text=original, new_text=promoted, version=args.version
    )
    args.changelog.write_text(promoted)


def _cmd_assert_lock_diff(args: argparse.Namespace) -> None:
    lock.assert_lock_diff_narrow(
        before_text=args.before.read_text(),
        after_text=args.after.read_text(),
        package=args.package,
    )


def _cmd_render_pr_body(args: argparse.Namespace) -> None:
    section_body = changelog.extract_released_section(
        changelog_text=args.changelog.read_text(), version=args.version
    )
    body = pr_body.render_pr_body(section_body=section_body, version=args.version)
    args.output.write_text(body)


def _cmd_check_ci(args: argparse.Namespace) -> None:
    required = ci_gate.parse_required_checks(json.loads(args.branch_rules.read_text()))
    print(f"Required checks, per the branch ruleset: {', '.join(required)}")
    verdicts = ci_gate.evaluate_check_runs(
        check_runs=ci_gate.parse_check_runs(json.loads(args.check_runs.read_text())),
        required=required,
    )
    report = ci_gate.render_report(verdicts=verdicts, sha=args.sha)
    print(report)
    if args.summary is not None:
        with args.summary.open("a") as summary:
            summary.write(report)

    failed = [verdict for verdict in verdicts if not verdict.passed]
    for verdict in failed:
        print(f"::error::Required check '{verdict.name}' {verdict.detail}. {verdict.url}".rstrip())
    if failed:
        raise PrepareReleaseError(
            f"{len(failed)} of {len(verdicts)} required checks are not green on {args.sha}; "
            "not releasing this commit."
        )


if __name__ == "__main__":
    sys.exit(main())
