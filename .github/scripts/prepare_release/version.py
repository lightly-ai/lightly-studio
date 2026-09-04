"""Version guards and the release version reader.

Bumping and writing the `[project]` version is left to
`uv version --bump` (see the Prepare Release workflow) rather than
reimplemented here - it already parses/writes real TOML and handles more
than plain X.Y.Z (alpha/beta/rc/post/dev), which regex-based text editing
kept getting subtly wrong in review. This module keeps the guard that `uv`
has no way to know about - whether Labelformat itself needs a release first -
and a plain reader for the Publish Release workflow, which must learn the
version to tag without resolving the project environment first. That reader
matches a line rather than parsing TOML: `tomllib` is 3.11+, and this CLI has
to stay importable on whatever `python3` a runner or a laptop provides.
"""

from __future__ import annotations

import re

from prepare_release.errors import PrepareReleaseError

_PROJECT_HEADER_RE = re.compile(r"^\[project\][ \t]*$", re.MULTILINE)
_ANY_HEADER_RE = re.compile(r"^\[", re.MULTILINE)
_VERSION_RE = re.compile(r"^version[ \t]*=[ \t]*[\"'](?P<version>[^\"']+)[\"']", re.MULTILINE)


def read_project_version(pyproject_text: str) -> str:
    """Reads the version out of the `[project]` table of a pyproject.toml.

    The tag comes from the package rather than from workflow input, so the two
    can never disagree. Only the `[project]` table is searched, so a `version`
    in a later table cannot be picked up by mistake.

    Raises:
        PrepareReleaseError: There is no `[project]` table, or it declares no
            plain `version = "..."`.
    """
    match = _VERSION_RE.search(_project_table(pyproject_text))
    if match is None:
        raise PrepareReleaseError('no plain `version = "..."` found in the [project] table')
    return match["version"]


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


def _project_table(pyproject_text: str) -> str:
    """Returns the body of the `[project]` table, up to the next table header."""
    header = _PROJECT_HEADER_RE.search(pyproject_text)
    if header is None:
        raise PrepareReleaseError("no [project] table found in pyproject.toml")
    next_header = _ANY_HEADER_RE.search(pyproject_text, header.end())
    end = next_header.start() if next_header else len(pyproject_text)
    return pyproject_text[header.end() : end]
