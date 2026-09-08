"""Assemble the GitHub release body: the changelog section, then GitHub's own notes.

Backs the "Draft Release" workflow. The `CHANGELOG.md` section leads because
it is the text the team edited and reviewed on the release PR; GitHub's
auto-generated notes follow as the full commit-level record.

Those generated notes are built from PR titles, which carry internal ticket
ids. `RELEASE.md` says to strip them by hand before publishing; this does it
as a regex.
"""

from __future__ import annotations

import re

# The changelog section starts at "### Added", so it needs a heading of its own
# to sit level with the "## What's Changed" of the generated half below it.
_CHANGELOG_HEADING = "## Changelog"

# Ticket ids as they occur in this repo's PR titles: leading "LIG-10603: ",
# leading "LIG-10374 ", and trailing "(LIG-10323)" or "(LIG-10089, 2/3)". A
# bare id mid-title is stripped too - it reads worse than the anchored cases,
# but an internal ticket id in public release notes is worse still. The
# trailing rule takes only the two shapes that occur, "(LIG-1)" and
# "(LIG-1, 2/3)", so a parenthetical carrying anything else keeps its text.
_LEADING_TICKET_RE = re.compile(r"^LIG[\s-]?\d+\s*:?\s+", re.IGNORECASE)
_TRAILING_TICKET_RE = re.compile(r"\s*\(LIG[\s-]?\d+(?:,\s*\d+/\d+)?\)", re.IGNORECASE)
_BARE_TICKET_RE = re.compile(r"\bLIG[\s-]?\d+\b", re.IGNORECASE)
_ORPHANED_COMMA_RE = re.compile(r"\(\s*,\s*")
_REPEATED_SPACE_RE = re.compile(r"  +")

# GitHub renders each pull request as "* <title> by @user in <url>".
_BULLET_RE = re.compile(r"^(?P<bullet>[*-] )(?P<title>.*)$")


def render_release_notes(changelog_section: str, generated_notes: str) -> str:
    """Assembles the release body from the changelog section and GitHub's notes.

    Args:
        changelog_section: The `[X.Y.Z]` block from `CHANGELOG.md`.
        generated_notes: The body returned by the releases/generate-notes API.

    Returns:
        The Markdown body for the GitHub release.
    """
    return (
        f"{_CHANGELOG_HEADING}\n\n"
        f"{changelog_section.strip()}\n\n"
        f"{sanitize_generated_notes(generated_notes).strip()}\n"
    )


def sanitize_generated_notes(notes: str) -> str:
    """Strips internal ticket ids from the pull request titles in GitHub's notes."""
    return "\n".join(_sanitize_line(line) for line in notes.splitlines())


def _sanitize_line(line: str) -> str:
    """Strips ticket ids from one bullet, leaving headings and prose untouched."""
    match = _BULLET_RE.match(line)
    if match is None:
        return line
    title = _LEADING_TICKET_RE.sub("", match["title"])
    title = _TRAILING_TICKET_RE.sub("", title)
    title = _ORPHANED_COMMA_RE.sub("(", _BARE_TICKET_RE.sub("", title))
    return f"{match['bullet']}{_REPEATED_SPACE_RE.sub(' ', title).strip()}"
