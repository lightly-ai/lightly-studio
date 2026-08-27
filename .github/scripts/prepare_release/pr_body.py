"""Render the release PR body: draft notes + advisory coverage checklist."""

from __future__ import annotations


def render_pr_body(section_body: str, coverage_checklist: str) -> str:
    """Assembles the release PR body: draft notes + advisory coverage checklist.

    The coverage checklist is git-derived and untrusted display text - it
    must never be mistaken for reviewed release notes, hence the explicit
    label and the blank line separating it from the draft notes.
    """
    checklist = coverage_checklist.strip() or "_None found._"
    return (
        "## Draft release notes\n\n"
        "> Mechanically promoted from CHANGELOG.md - review and edit before publishing.\n\n"
        f"{section_body}\n\n"
        "## Coverage checklist (advisory only - never copy into the release notes)\n\n"
        "Merged changes since the last tag with no obviously matching CHANGELOG entry, "
        "for a human to judge:\n\n"
        f"{checklist}\n"
    )
