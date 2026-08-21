"""Version bump math and pyproject.toml / Labelformat guards."""

from __future__ import annotations

import re

from prepare_release.errors import PrepareReleaseError

_PYPROJECT_VERSION_RE = re.compile(r'^version = "(?P<version>[^"]+)"$', re.MULTILINE)
_SEMVER_PART_COUNT = 3


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
