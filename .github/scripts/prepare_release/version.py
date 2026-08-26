"""Version bump math and pyproject.toml / Labelformat guards."""

from __future__ import annotations

import re

from prepare_release.errors import PrepareReleaseError

_PROJECT_SECTION_RE = re.compile(r"^\[project\]\r?\n(?:(?!^\[).*(?:\r?\n|\Z))*", re.MULTILINE)
_PYPROJECT_VERSION_RE = re.compile(
    r'^[ \t]*version[ \t]*=[ \t]*"(?P<version>[^"]+)"(?=\r?$)', re.MULTILINE
)
_SEMVER_PART_RE = re.compile(r"(?:0|[1-9][0-9]*)")
_SEMVER_PART_COUNT = 3


def current_pyproject_version(pyproject_text: str) -> str:
    """Reads the `[project] version` from a `pyproject.toml`'s text."""
    section = _project_section(pyproject_text).group(0)
    match = _PYPROJECT_VERSION_RE.search(section)
    if match is None:
        raise PrepareReleaseError(
            'no `version = "..."` line found in the `[project]` table of pyproject.toml'
        )
    return match.group("version")


def bump_semver(version: str, bump: str) -> str:
    """Bumps a plain `X.Y.Z` version.

    Args:
        version: The current version. Must be exactly `X.Y.Z` with integer
            parts and no leading zeroes (per semver.org's grammar);
            anything else (e.g. an already-released release candidate) has
            no well-defined next bump and should be overridden explicitly
            instead.
        bump: One of "patch", "minor", "major".

    Returns:
        The bumped version, still in plain `X.Y.Z` form.
    """
    parts = version.split(".")
    if len(parts) != _SEMVER_PART_COUNT or not all(_SEMVER_PART_RE.fullmatch(p) for p in parts):
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
    fine. Matched per line with `#`-comments stripped first (so a
    commented-out example doesn't false-positive), not anchored to the
    line's start (so a non-first entry in an inline array still is caught).
    """
    for line in pyproject_text.splitlines():
        active = line.split("#", 1)[0]
        for match in re.finditer(r'(?P<quote>["\'])labelformat[^"\']*\1', active, re.IGNORECASE):
            if "git+" in match.group(0):
                raise PrepareReleaseError(
                    "labelformat is pinned by git sha in pyproject.toml "
                    f"({match.group(0).strip()}). Release Labelformat first, see "
                    "https://www.notion.so/Release-Labelformat-or-Lightly-Insights-"
                    "039ffe75cd8b4dd89dcb45a7338533b2?source=copy_link"
                )


def bump_pyproject_version(pyproject_text: str, new_version: str) -> str:
    """Returns `pyproject_text` with the `[project] version` replaced."""
    section_match = _project_section(pyproject_text)
    new_section, count = _PYPROJECT_VERSION_RE.subn(
        f'version = "{new_version}"', section_match.group(0), count=1
    )
    if count == 0:
        raise PrepareReleaseError(
            'no `version = "..."` line found in the `[project]` table of pyproject.toml'
        )
    return (
        pyproject_text[: section_match.start()]
        + new_section
        + pyproject_text[section_match.end() :]
    )


def _project_section(pyproject_text: str) -> re.Match[str]:
    """Locates the `[project]` table's text span, header included.

    Scoping to this span (rather than searching the whole file) keeps a
    `version = "..."` line in some other table, e.g. `[tool.foo]`, from
    being mistaken for the release version.
    """
    match = _PROJECT_SECTION_RE.search(pyproject_text)
    if match is None:
        raise PrepareReleaseError("no `[project]` table found in pyproject.toml")
    return match
