"""Render the release PR body: the draft release notes."""

from __future__ import annotations


def render_pr_body(section_body: str) -> str:
    """Assembles the release PR body: the draft release notes.

    section_body is the CHANGELOG section already promoted for this version.
    """
    return (
        "## Draft release notes\n\n"
        "> Mechanically promoted from CHANGELOG.md - review and edit before publishing.\n\n"
        f"{section_body}\n"
    )
