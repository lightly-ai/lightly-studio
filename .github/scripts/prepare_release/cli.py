"""Command-line entry point for the prepare-release tooling.

Backs the "Prepare Release" GitHub Actions workflow
(`.github/workflows/prepare_release.yml`). Each subcommand does one small,
independently testable piece of preparing a release: promoting the
changelog, bumping the version, and guarding against a handful of ways
that can quietly go wrong.

Usage:
    python -m prepare_release suggest-bump --changelog CHANGELOG.md
    python -m prepare_release promote-changelog --changelog CHANGELOG.md \
        --version 1.0.6 --date 2026-08-21
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from prepare_release import changelog, lock, pr_body, version
from prepare_release.errors import PrepareReleaseError


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: parses `argv`, dispatches to the matching subcommand."""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_pin = subparsers.add_parser(
        "check-labelformat-pin", help="fail if labelformat is pinned by git sha"
    )
    check_pin.add_argument("--pyproject", type=Path, required=True)

    suggest = subparsers.add_parser(
        "suggest-bump", help="suggest a semver bump from [Unreleased]'s contents"
    )
    suggest.add_argument("--changelog", type=Path, required=True)

    compute = subparsers.add_parser(
        "compute-version", help="resolve the release version to bump to"
    )
    compute.add_argument("--pyproject", type=Path, required=True)
    compute.add_argument("--bump", choices=["patch", "minor", "major"], required=True)
    compute.add_argument("--version", default="", help="explicit override, empty to use --bump")

    promote = subparsers.add_parser(
        "promote-changelog", help="promote [Unreleased] to a released version block"
    )
    promote.add_argument("--changelog", type=Path, required=True)
    promote.add_argument("--version", required=True)
    promote.add_argument("--date", required=True, help="YYYY-MM-DD")

    bump_pyproject = subparsers.add_parser(
        "bump-pyproject", help="write the new version into pyproject.toml"
    )
    bump_pyproject.add_argument("--pyproject", type=Path, required=True)
    bump_pyproject.add_argument("--version", required=True)

    lock_diff = subparsers.add_parser(
        "assert-lock-diff", help="fail if uv sync changed more than the version bump"
    )
    lock_diff.add_argument("--before", type=Path, required=True)
    lock_diff.add_argument("--after", type=Path, required=True)
    lock_diff.add_argument("--package", required=True)

    pr_body_parser = subparsers.add_parser("render-pr-body", help="assemble the release PR body")
    pr_body_parser.add_argument("--changelog", type=Path, required=True)
    pr_body_parser.add_argument("--version", required=True)
    pr_body_parser.add_argument("--drafting-skipped-reason", required=True)
    pr_body_parser.add_argument("--coverage-file", type=Path, required=True)
    pr_body_parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args(argv)

    try:
        return _dispatch(args)
    except PrepareReleaseError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


def _dispatch(args: argparse.Namespace) -> int:
    handlers = {
        "check-labelformat-pin": _cmd_check_labelformat_pin,
        "suggest-bump": _cmd_suggest_bump,
        "compute-version": _cmd_compute_version,
        "promote-changelog": _cmd_promote_changelog,
        "bump-pyproject": _cmd_bump_pyproject,
        "assert-lock-diff": _cmd_assert_lock_diff,
        "render-pr-body": _cmd_render_pr_body,
    }
    handlers[args.command](args)
    return 0


def _cmd_check_labelformat_pin(args: argparse.Namespace) -> None:
    version.check_labelformat_pin(args.pyproject.read_text())


def _cmd_suggest_bump(args: argparse.Namespace) -> None:
    sections = changelog.parse_unreleased_sections(args.changelog.read_text())
    bump, reasoning = changelog.suggest_bump(sections)
    print(f"bump={bump}")
    print(reasoning)


def _cmd_compute_version(args: argparse.Namespace) -> None:
    if args.version:
        print(args.version)
        return
    current = version.current_pyproject_version(args.pyproject.read_text())
    print(version.bump_semver(current, args.bump))


def _cmd_promote_changelog(args: argparse.Namespace) -> None:
    original = args.changelog.read_text()
    promoted = changelog.promote_changelog(original, args.version, args.date)
    changelog.assert_changelog_structure(original, promoted, args.version)
    args.changelog.write_text(promoted)


def _cmd_bump_pyproject(args: argparse.Namespace) -> None:
    original = args.pyproject.read_text()
    args.pyproject.write_text(version.bump_pyproject_version(original, args.version))


def _cmd_assert_lock_diff(args: argparse.Namespace) -> None:
    lock.assert_lock_diff_narrow(
        args.before.read_text(), args.after.read_text(), package=args.package
    )


def _cmd_render_pr_body(args: argparse.Namespace) -> None:
    section_body = changelog.extract_released_section(args.changelog.read_text(), args.version)
    coverage_checklist = args.coverage_file.read_text() if args.coverage_file.exists() else ""
    body = pr_body.render_pr_body(section_body, args.drafting_skipped_reason, coverage_checklist)
    args.output.write_text(body)


if __name__ == "__main__":
    sys.exit(main())
