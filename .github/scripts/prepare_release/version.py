"""Labelformat git-pin guard.

Reading, bumping, and writing the `[project]` version is left to
`uv version --bump` (see the Prepare Release workflow) rather than
reimplemented here - it already parses/writes real TOML and handles more
than plain X.Y.Z (alpha/beta/rc/post/dev), which regex-based text editing
kept getting subtly wrong in review. This module keeps only the guard that
`uv` has no way to know about: whether Labelformat itself needs a release
first.
"""

from __future__ import annotations

import re

from prepare_release.errors import PrepareReleaseError


def check_labelformat_pin(pyproject_text: str) -> None:
    """Fails if the Labelformat requirement is pinned by git sha.

    A `git+` requirement means Labelformat itself needs a release first
    (see the Labelformat release runbook); a plain version requirement is
    fine. Matched per line with a trailing `#`-comment stripped first (so a
    commented-out example doesn't false-positive), not anchored to the
    line's start (so a non-first entry in an inline array still is caught).
    """
    for line in pyproject_text.splitlines():
        active = _strip_comment(line)
        for match in re.finditer(r'(?P<quote>["\'])labelformat[^"\']*\1', active, re.IGNORECASE):
            if "git+" in match.group(0):
                raise PrepareReleaseError(
                    "labelformat is pinned by git sha in pyproject.toml "
                    f"({match.group(0).strip()}). Release Labelformat first, see "
                    "https://www.notion.so/Release-Labelformat-or-Lightly-Insights-"
                    "039ffe75cd8b4dd89dcb45a7338533b2?source=copy_link"
                )


def _strip_comment(line: str) -> str:
    """Removes a trailing `#` comment, ignoring a `#` inside a quoted string.

    E.g. a `#egg=...` URL fragment inside a `"... @ git+https://...#egg=..."`
    dependency string is not mistaken for a comment.
    """
    quote = None
    for i, char in enumerate(line):
        if quote:
            quote = None if char == quote else quote
        elif char in "\"'":
            quote = char
        elif char == "#":
            return line[:i]
    return line
