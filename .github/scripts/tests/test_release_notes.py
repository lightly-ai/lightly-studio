from __future__ import annotations

import pytest

from prepare_release import release_notes

GENERATED = """\
## What's Changed
* LIG-10603: Compare metadata distributions by sample tags by @dev in https://x/pull/2096
* LIG-10374 Add GCS cloud credential runtime support by @dev in https://x/pull/1844
* Backend, Part 0: Fix typo in parameter test filename (LIG-10323) by @dev in https://x/pull/1797
* Show an image preview when hovering (LIG-10089, 3/3) by @dev in https://x/pull/1561
* Fix: Update caption item view by @dev in https://x/pull/2151

**Full Changelog**: https://x/compare/v1.0.4...v1.0.5
"""


def test_render_release_notes():
    body = release_notes.render_release_notes(
        changelog_section="### Added\n\n- A thing.", generated_notes="## What's Changed\n* A by @d"
    )

    assert body == (
        "### Added\n\n- A thing.\n\n<!-- STOP DISCORD MESSAGE -->\n\n## What's Changed\n* A by @d\n"
    )


# Discord caps the message body, so the marker must precede the generated notes.
def test_render_release_notes__marker_precedes_the_generated_notes():
    body = release_notes.render_release_notes(
        changelog_section="### Added\n\n- A thing.", generated_notes="## What's Changed\n* A by @d"
    )

    assert body.index(release_notes.DISCORD_STOP_MARKER) < body.index("What's Changed")


def test_sanitize_generated_notes():
    sanitized = release_notes.sanitize_generated_notes(GENERATED)

    assert "LIG" not in sanitized
    assert sanitized.splitlines()[1].startswith("* Compare metadata distributions by sample tags")


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("LIG-10603: Compare distributions", "Compare distributions"),
        ("LIG-10374 Add GCS support", "Add GCS support"),
        ("lig 10374 Add GCS support", "Add GCS support"),
        ("Fix typo in filename (LIG-10323)", "Fix typo in filename"),
        ("Show a preview (LIG-10089, 3/3)", "Show a preview"),
        ("Fix: Update caption item view", "Fix: Update caption item view"),
        ("Add support for LIGHTLY tokens", "Add support for LIGHTLY tokens"),
        # A bare id mid-title is not anchored at either end, so it needs its
        # own rule; the result reads a little thin, which beats leaking it.
        ("Fix the LIG-10603 regression", "Fix the regression"),
        ("Revert LIG 10374 and retry", "Revert and retry"),
        # Only "(LIG-1)" and "(LIG-1, 2/3)" are dropped whole; a parenthetical
        # carrying anything else keeps the rest of its text.
        ("Document migration (LIG-123, breaking change)", "Document migration (breaking change)"),
        ("Show a preview (LIG-10089, 1/3)", "Show a preview"),
    ],
)
def test_sanitize_generated_notes__pull_request_titles(title: str, expected: str):
    line = f"* {title} by @dev in https://x/pull/1"

    assert (
        release_notes.sanitize_generated_notes(line) == f"* {expected} by @dev in https://x/pull/1"
    )


# Headings and the trailing "Full Changelog" line are not pull request titles.
def test_sanitize_generated_notes__leaves_non_bullet_lines_alone():
    notes = "## What's Changed\n**Full Changelog**: https://x/compare/v1.0.4...v1.0.5"

    assert release_notes.sanitize_generated_notes(notes) == notes
