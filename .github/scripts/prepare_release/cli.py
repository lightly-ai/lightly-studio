"""Command-line entry point for the release tooling.

Backs the "Prepare Release" and "Publish Release" GitHub Actions workflows.
Each subcommand does one small, independently testable piece of preparing or
publishing a release: promoting the changelog, assembling the release notes,
and guarding against a handful of ways those can quietly go wrong. Bumping
and writing the `[project]` version is left to `uv version --bump` directly
in the workflow (see version.py's docstring); `read-version` only reads it.

Usage:
    python -m prepare_release promote-changelog --changelog CHANGELOG.md \
        --version 1.0.6 --date 2026-08-21
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from prepare_release import changelog, lock, pr_body, release_notes, version
from prepare_release.errors import PrepareReleaseError

CHECK_LABELFORMAT_PIN = "check-labelformat-pin"
PROMOTE_CHANGELOG = "promote-changelog"
ASSERT_LOCK_DIFF = "assert-lock-diff"
RENDER_PR_BODY = "render-pr-body"
READ_VERSION = "read-version"
RENDER_RELEASE_NOTES = "render-release-notes"


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

    read_version = subparsers.add_parser(
        READ_VERSION, help="print the [project] version of a pyproject.toml"
    )
    read_version.add_argument("--pyproject", type=Path, required=True)

    release_notes_parser = subparsers.add_parser(
        RENDER_RELEASE_NOTES, help="assemble the GitHub release body"
    )
    release_notes_parser.add_argument("--changelog", type=Path, required=True)
    release_notes_parser.add_argument("--version", required=True)
    release_notes_parser.add_argument(
        "--generated",
        type=Path,
        required=True,
        help="body from the `releases/generate-notes` API",
    )
    release_notes_parser.add_argument("--output", type=Path, required=True)

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
        READ_VERSION: _cmd_read_version,
        RENDER_RELEASE_NOTES: _cmd_render_release_notes,
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


def _cmd_read_version(args: argparse.Namespace) -> None:
    print(version.read_project_version(args.pyproject.read_text()))


def _cmd_render_release_notes(args: argparse.Namespace) -> None:
    section = changelog.extract_released_section(
        changelog_text=args.changelog.read_text(), version=args.version
    )
    body = release_notes.render_release_notes(
        changelog_section=section, generated_notes=args.generated.read_text()
    )
    args.output.write_text(body)


if __name__ == "__main__":
    sys.exit(main())
