#!/usr/bin/env python3
"""Mechanical steps for preparing a LightlyStudio release.

Backs the `Prepare Release` GitHub Actions workflow
(`.github/workflows/prepare_release.yml`). Every subcommand does one small,
independently testable piece of RELEASE.md steps 3-5: promoting the
changelog, bumping the version, and guarding against a handful of ways that
can quietly go wrong. See LIG-10552 for the full spec.

Stdlib only, deliberately: this runs on the release-critical path before
`uv sync`, so it must not itself depend on anything `uv` would need to
resolve first.

Usage (see `main()` for the full set of subcommands):
    python scripts/prepare_release.py suggest-bump --changelog CHANGELOG.md
    python scripts/prepare_release.py promote-changelog --changelog CHANGELOG.md \
        --version 1.0.6 --date 2026-08-21
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from pathlib import Path

# Keep a Changelog subsection headings, in the fixed order RELEASE.md and the
# existing CHANGELOG.md use.
SUBSECTIONS = ("Added", "Changed", "Deprecated", "Removed", "Fixed", "Security")

# `## [Unreleased]` is the one heading kept unescaped; every released version
# heading is `## \[X.Y.Z\] - YYYY-MM-DD` (see LIG-10552 for why that split
# matters). Getting this backwards silently breaks the convention instead of
# failing loudly, which is exactly what `assert_changelog_structure` guards.
_UNRELEASED_RE = re.compile(r"^## \[Unreleased\][ \t]*$", re.MULTILINE)
_ANY_H2_RE = re.compile(r"^## ", re.MULTILINE)
_SUBSECTION_RE = re.compile(r"^### (?P<name>\w+)[ \t]*$", re.MULTILINE)
_PYPROJECT_VERSION_RE = re.compile(r'^version = "(?P<version>[^"]+)"$', re.MULTILINE)
_LOCK_PACKAGE_SPLIT_RE = re.compile(r"(?=^\[\[package\]\]$)", re.MULTILINE)
_LOCK_PACKAGE_NAME_RE = re.compile(r'^name = "(?P<name>[^"]+)"$', re.MULTILINE)
_SEMVER_PART_COUNT = 3


class PrepareReleaseError(Exception):
    """A release-preparation precondition failed.

    Raised for anything that should fail the workflow loudly rather than
    open a malformed or unreviewable release PR.
    """


def current_pyproject_version(pyproject_text: str) -> str:
    """Reads the `[project] version` from a `pyproject.toml`'s text."""
    match = _PYPROJECT_VERSION_RE.search(pyproject_text)
    if match is None:
        raise PrepareReleaseError('no `version = "..."` line found in pyproject.toml')
    return match.group("version")


def bump_semver(version: str, bump: str) -> str:
    """Bumps a plain `X.Y.Z` version.

    Args:
        version: The current version. Must be exactly `X.Y.Z` with integer
            parts; anything else (e.g. an already-released release
            candidate) has no well-defined next bump and should be
            overridden explicitly instead.
        bump: One of "patch", "minor", "major".

    Returns:
        The bumped version, still in plain `X.Y.Z` form.
    """
    parts = version.split(".")
    if len(parts) != _SEMVER_PART_COUNT or not all(p.isdigit() for p in parts):
        raise PrepareReleaseError(
            f"current version {version!r} is not a plain X.Y.Z semver; "
            "pass --version explicitly instead of a --bump"
        )
    major, minor, patch = (int(p) for p in parts)
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    if bump == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise PrepareReleaseError(f"unknown bump kind {bump!r}")


def check_labelformat_pin(pyproject_text: str) -> None:
    """Fails if the Labelformat requirement is pinned by git sha.

    A `git+` requirement means Labelformat itself needs a release first
    (see the Labelformat release runbook); a plain version requirement is
    fine.
    """
    match = re.search(r'^\s*"labelformat[^"]*"', pyproject_text, re.MULTILINE)
    if match and "git+" in match.group(0):
        raise PrepareReleaseError(
            "labelformat is pinned by git sha in pyproject.toml "
            f"({match.group(0).strip()}). Release Labelformat first, see "
            "https://www.notion.so/Release-Labelformat-or-Lightly-Insights-"
            "039ffe75cd8b4dd89dcb45a7338533b2?source=copy_link"
        )


def bump_pyproject_version(pyproject_text: str, new_version: str) -> str:
    """Returns `pyproject_text` with the `[project] version` replaced."""
    new_text, count = _PYPROJECT_VERSION_RE.subn(
        f'version = "{new_version}"', pyproject_text, count=1
    )
    if count == 0:
        raise PrepareReleaseError('no `version = "..."` line found in pyproject.toml')
    return new_text


def parse_unreleased_sections(changelog_text: str) -> dict[str, str]:
    """Extracts the `[Unreleased]` section's six subsections.

    Returns:
        A mapping from subsection name (e.g. "Added") to its raw body text
        (may be empty or whitespace-only).
    """
    body = _unreleased_body(changelog_text)
    headings = list(_SUBSECTION_RE.finditer(body))
    names = [h.group("name") for h in headings]
    if names != list(SUBSECTIONS):
        raise PrepareReleaseError(
            f"[Unreleased] subsections are {names}, expected {list(SUBSECTIONS)} in that order"
        )
    sections = {}
    for i, heading in enumerate(headings):
        start = heading.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(body)
        sections[heading.group("name")] = body[start:end]
    return sections


def suggest_bump(sections: dict[str, str]) -> tuple[str, str]:
    """Suggests a semver bump from which [Unreleased] sections are non-empty.

    Added / Changed / Removed / Deprecated entries suggest a minor bump;
    only Fixed and/or Security entries suggest a patch. The operator still
    confirms - this is a suggestion, not a decision.
    """
    non_empty = [name for name in SUBSECTIONS if sections.get(name, "").strip()]
    if not non_empty:
        raise PrepareReleaseError("the [Unreleased] section has no entries; nothing to release")
    minor_triggers = [n for n in non_empty if n in ("Added", "Changed", "Removed", "Deprecated")]
    bump = "minor" if minor_triggers else "patch"
    reasoning = f"Non-empty [Unreleased] sections: {', '.join(non_empty)}."
    return bump, reasoning


def promote_changelog(changelog_text: str, version: str, date: str) -> str:
    """Promotes `[Unreleased]` to a released version block.

    Drops empty subsections from the promoted block, inserts a fresh empty
    `[Unreleased]` skeleton above it, and leaves everything else byte-for-byte
    unchanged. Callers must run `assert_changelog_structure` on the result
    before trusting it - this function only constructs, it doesn't verify.
    """
    unreleased_match = _single_unreleased_match(changelog_text)
    _, body_end = _unreleased_body_span(changelog_text, unreleased_match)
    sections = parse_unreleased_sections(changelog_text)

    preamble = changelog_text[: unreleased_match.start()]
    rest = changelog_text[body_end:]

    skeleton = "## [Unreleased]\n\n" + "".join(f"### {name}\n\n" for name in SUBSECTIONS)

    promoted_sections = "".join(
        f"### {name}\n\n{sections[name].strip()}\n\n"
        for name in SUBSECTIONS
        if sections[name].strip()
    )
    promoted = f"## \\[{version}\\] - {date}\n\n" + promoted_sections

    return preamble + skeleton + promoted + rest


def assert_changelog_structure(original_text: str, new_text: str, version: str) -> None:
    r"""Verifies a changelog promotion didn't corrupt the file.

    Independently re-derives the required invariants from `new_text` rather
    than trusting how it was built, so it catches bugs in the construction
    logic itself:

    * exactly one `## [Unreleased]` heading, with all six subheadings,
    * the new `## \\[version\\] - YYYY-MM-DD` heading exists,
    * every previously-released version block is byte-identical to before.
    """
    unreleased_matches = list(_UNRELEASED_RE.finditer(new_text))
    if len(unreleased_matches) != 1:
        raise PrepareReleaseError(
            f"expected exactly one [Unreleased] heading after promotion, found "
            f"{len(unreleased_matches)}"
        )
    # Raises PrepareReleaseError itself if a subheading is missing/misordered.
    parse_unreleased_sections(new_text)

    released_heading = re.compile(
        r"^## \\\[" + re.escape(version) + r"\\\] - \d{4}-\d{2}-\d{2}[ \t]*$",
        re.MULTILINE,
    )
    if not released_heading.search(new_text):
        raise PrepareReleaseError(
            f"expected an escaped '## \\[{version}\\] - YYYY-MM-DD' heading after promotion"
        )

    original_match = _single_unreleased_match(original_text)
    _, original_body_end = _unreleased_body_span(original_text, original_match)
    previously_released = original_text[original_body_end:]
    if not new_text.endswith(previously_released):
        raise PrepareReleaseError(
            "previously-released changelog blocks are not byte-identical after promotion"
        )


def extract_released_section(changelog_text: str, version: str) -> str:
    r"""Returns the (trimmed) body of the `## \[version\] - ...` block."""
    heading = re.compile(
        r"^## \\\[" + re.escape(version) + r"\\\] - \d{4}-\d{2}-\d{2}[ \t]*$",
        re.MULTILINE,
    )
    match = heading.search(changelog_text)
    if match is None:
        raise PrepareReleaseError(f"no promoted heading found for version {version!r}")
    body_start = match.end()
    next_heading = _ANY_H2_RE.search(changelog_text, body_start)
    body_end = next_heading.start() if next_heading else len(changelog_text)
    return changelog_text[body_start:body_end].strip()


def render_pr_body(section_body: str, drafting_skipped_reason: str, coverage_checklist: str) -> str:
    """Assembles the release PR body: draft notes + advisory coverage checklist.

    The coverage checklist is git-derived and untrusted display text - it
    must never be mistaken for reviewed release notes, hence the explicit
    label and the blank line separating it from the draft notes.
    """
    checklist = coverage_checklist.strip() or "_None found._"
    return (
        "## Draft release notes\n\n"
        f"> Automated drafting was skipped ({drafting_skipped_reason}). These are the "
        "mechanically promoted CHANGELOG entries - review and edit before publishing.\n\n"
        f"{section_body}\n\n"
        "## Coverage checklist (advisory only - never copy into the release notes)\n\n"
        "Merged changes since the last tag with no obviously matching CHANGELOG entry, "
        "for a human to judge:\n\n"
        f"{checklist}\n"
    )


def parse_lock_blocks(uv_lock_text: str) -> dict[str, str]:
    """Splits a `uv.lock`'s text into per-package blocks, keyed by name.

    The lockfile header (everything before the first `[[package]]`) is kept
    under the empty-string key so it participates in the same diff check.
    """
    chunks = _LOCK_PACKAGE_SPLIT_RE.split(uv_lock_text)
    blocks = {"": chunks[0]}
    for chunk in chunks[1:]:
        match = _LOCK_PACKAGE_NAME_RE.search(chunk)
        if match is None:
            raise PrepareReleaseError("a uv.lock [[package]] block has no `name` field")
        blocks[match.group("name")] = chunk
    return blocks


def assert_lock_diff_narrow(before_text: str, after_text: str, package: str) -> None:
    """Fails if `uv sync` changed more than `package`'s version line.

    `uv sync` on CI can resolve transitive dependencies differently from
    whoever last locked, producing a diff wider than the version bump. That
    doesn't endanger the published wheel, but it makes the release PR
    unreviewable, so treat it as a hard failure rather than something review
    might catch.
    """
    before_blocks = parse_lock_blocks(before_text)
    after_blocks = parse_lock_blocks(after_text)

    unexpected = sorted(
        name or "<lockfile header>"
        for name in set(before_blocks) | set(after_blocks)
        if name != package and before_blocks.get(name) != after_blocks.get(name)
    )
    if unexpected:
        raise PrepareReleaseError(
            "uv sync changed packages beyond the version bump: " + ", ".join(unexpected)
        )

    before_pkg = before_blocks.get(package)
    after_pkg = after_blocks.get(package)
    if before_pkg is None or after_pkg is None:
        raise PrepareReleaseError(f"package {package!r} not found in uv.lock before/after uv sync")

    diff = difflib.unified_diff(before_pkg.splitlines(), after_pkg.splitlines(), lineterm="")
    changed_lines = [line for line in diff if line[:1] in "+-" and line[:3] not in ("+++", "---")]
    if any(not re.match(r'^[+-]version = "', line) for line in changed_lines):
        raise PrepareReleaseError(
            f"uv.lock diff for {package!r} touches more than its version line:\n"
            + "\n".join(changed_lines)
        )


def _single_unreleased_match(changelog_text: str) -> re.Match[str]:
    matches = list(_UNRELEASED_RE.finditer(changelog_text))
    if len(matches) != 1:
        raise PrepareReleaseError(
            f"expected exactly one [Unreleased] heading, found {len(matches)}"
        )
    return matches[0]


def _unreleased_body_span(changelog_text: str, unreleased_match: re.Match[str]) -> tuple[int, int]:
    body_start = unreleased_match.end()
    next_heading = _ANY_H2_RE.search(changelog_text, body_start)
    body_end = next_heading.start() if next_heading else len(changelog_text)
    return body_start, body_end


def _unreleased_body(changelog_text: str) -> str:
    match = _single_unreleased_match(changelog_text)
    start, end = _unreleased_body_span(changelog_text, match)
    return changelog_text[start:end]


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

    pr_body = subparsers.add_parser("render-pr-body", help="assemble the release PR body")
    pr_body.add_argument("--changelog", type=Path, required=True)
    pr_body.add_argument("--version", required=True)
    pr_body.add_argument("--drafting-skipped-reason", required=True)
    pr_body.add_argument("--coverage-file", type=Path, required=True)
    pr_body.add_argument("--output", type=Path, required=True)

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
    check_labelformat_pin(args.pyproject.read_text())


def _cmd_suggest_bump(args: argparse.Namespace) -> None:
    sections = parse_unreleased_sections(args.changelog.read_text())
    bump, reasoning = suggest_bump(sections)
    print(f"bump={bump}")
    print(reasoning)


def _cmd_compute_version(args: argparse.Namespace) -> None:
    if args.version:
        print(args.version)
        return
    current = current_pyproject_version(args.pyproject.read_text())
    print(bump_semver(current, args.bump))


def _cmd_promote_changelog(args: argparse.Namespace) -> None:
    original = args.changelog.read_text()
    promoted = promote_changelog(original, args.version, args.date)
    assert_changelog_structure(original, promoted, args.version)
    args.changelog.write_text(promoted)


def _cmd_bump_pyproject(args: argparse.Namespace) -> None:
    original = args.pyproject.read_text()
    args.pyproject.write_text(bump_pyproject_version(original, args.version))


def _cmd_assert_lock_diff(args: argparse.Namespace) -> None:
    assert_lock_diff_narrow(args.before.read_text(), args.after.read_text(), package=args.package)


def _cmd_render_pr_body(args: argparse.Namespace) -> None:
    section_body = extract_released_section(args.changelog.read_text(), args.version)
    coverage_checklist = args.coverage_file.read_text() if args.coverage_file.exists() else ""
    body = render_pr_body(section_body, args.drafting_skipped_reason, coverage_checklist)
    args.output.write_text(body)


if __name__ == "__main__":
    sys.exit(main())
