"""Guard the requirement one workspace member declares on another.

uv resolves a workspace dependency from the workspace and drops the declared
specifier: `uv.lock` records the member with no `specifier` field, where every
registry dependency keeps one. So `uv lock`, `uv sync` and `uv lock --check` pass
whatever the requirement says, and the range that ships in the wheel is never
exercised. `assert_admits_version` and `assert_floor_published` exercise it.

Version handling is deliberately narrow: `X.Y.Z` with an optional PEP 440
pre-release suffix, which is everything this repository publishes, and a refusal
rather than a wrong comparison for anything else.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from collections.abc import Sequence

from prepare_release import version as version_module
from prepare_release.errors import PrepareReleaseError

_PYPI_URL = "https://pypi.org/pypi/{distribution}/json"
_NOT_FOUND = 404

_SPECIFIER_RE = re.compile(r"(?P<operator>[<>=!~]=|[<>])\s*(?P<version>[^,\s]+)")
_VERSION_RE = re.compile(r"^(?P<release>\d+(?:\.\d+)*)(?:(?P<kind>a|b|rc)(?P<number>\d+))?$")
_PRE_RELEASE_ORDER = {"a": 0, "b": 1, "rc": 2}

_COMPARISONS = {
    "==": lambda actual, bound: actual == bound,
    "!=": lambda actual, bound: actual != bound,
    ">=": lambda actual, bound: actual >= bound,
    "<=": lambda actual, bound: actual <= bound,
    ">": lambda actual, bound: actual > bound,
    "<": lambda actual, bound: actual < bound,
}


def assert_admits_version(pyproject_text: str, dependency: str, dependency_version: str) -> None:
    """Fails if the requirement on `dependency` excludes the version it resolves to.

    Args:
        pyproject_text: The dependent package's pyproject.toml.
        dependency: The distribution name of the workspace dependency.
        dependency_version: The `[project]` version of that workspace member.

    Raises:
        PrepareReleaseError: There is no such requirement, or it does not admit
            `dependency_version`.
    """
    requirement = read_requirement(pyproject_text=pyproject_text, distribution=dependency)
    if not admits(requirement=requirement, candidate=dependency_version):
        raise PrepareReleaseError(
            f"the workspace builds and tests against {dependency} {dependency_version}, but "
            f"the requirement {requirement!r} excludes it. The wheel would declare a range "
            "that this repository never ran. Widen the requirement, or release the "
            "dependency at a version the range admits."
        )


def assert_floor_published(
    pyproject_text: str, dependency: str, published_versions: Sequence[str]
) -> None:
    """Fails if the requirement's lower bound is not among `published_versions`.

    Raises:
        PrepareReleaseError: The requirement has no lower bound, or the version it
            names was never published.
    """
    requirement = read_requirement(pyproject_text=pyproject_text, distribution=dependency)
    floor = floor_of(requirement)
    floor_key = _version_key(floor)
    if not any(_version_key_or_none(candidate) == floor_key for candidate in published_versions):
        raise PrepareReleaseError(
            f"the requirement {requirement!r} has a floor of {floor}, which is not published. "
            f"Anyone installing this package would fail to resolve it. Release {dependency} "
            f"{floor} first, or lower the floor to a version that exists."
        )


def read_published_versions(distribution: str) -> list[str]:
    """Returns every version of `distribution` published on PyPI.

    Raises:
        PrepareReleaseError: The project does not exist, or the index could not be
            read. A release gate fails loudly rather than assuming the best.
    """
    url = _PYPI_URL.format(distribution=distribution)
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == _NOT_FOUND:
            raise PrepareReleaseError(f"{distribution} is not published on PyPI at all") from error
        raise PrepareReleaseError(f"could not read {url}: HTTP {error.code}") from error
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as error:
        raise PrepareReleaseError(f"could not read {url}: {error}") from error
    return list(payload.get("releases", {}))


def read_requirement(pyproject_text: str, distribution: str) -> str:
    """Returns the dependency string declaring `distribution`, e.g. `foo>=1.0,<2.0`.

    Matched per line with a trailing comment stripped first, the same way the
    Labelformat guard does, so a commented-out example cannot be picked up.

    Raises:
        PrepareReleaseError: No such requirement is declared.
    """
    pattern = re.compile(
        r"(?P<quote>[\"'])(?P<requirement>"
        + re.escape(distribution)
        + r"(?![\w.-])[^\"']*)(?P=quote)"
    )
    for line in pyproject_text.splitlines():
        match = pattern.search(version_module.strip_comment(line))
        if match is not None:
            return match["requirement"].strip()
    raise PrepareReleaseError(f"no requirement on {distribution!r} found in pyproject.toml")


def floor_of(requirement: str) -> str:
    """Returns the version named by the requirement's `>=` or `==` bound.

    Raises:
        PrepareReleaseError: The requirement declares no lower bound. An unbounded
            requirement on a package released from this repository is a mistake:
            it would resolve to anything ever published, including versions from
            before the API the dependent package uses.
    """
    for operator, bound in parse_specifiers(requirement):
        if operator in (">=", "=="):
            return bound
    raise PrepareReleaseError(
        f"the requirement {requirement!r} declares no `>=` or `==` lower bound"
    )


def admits(requirement: str, candidate: str) -> bool:
    """Whether every specifier in `requirement` accepts `candidate`."""
    candidate_key = _version_key(candidate)
    return all(
        _COMPARISONS[operator](candidate_key, _version_key(bound))
        for operator, bound in parse_specifiers(requirement)
    )


def parse_specifiers(requirement: str) -> list[tuple[str, str]]:
    """Returns the `(operator, version)` pairs of a requirement string.

    Raises:
        PrepareReleaseError: The requirement carries no specifier, or one this
            check does not implement.
    """
    specifiers = [
        (match["operator"], match["version"]) for match in _SPECIFIER_RE.finditer(requirement)
    ]
    if not specifiers:
        raise PrepareReleaseError(f"the requirement {requirement!r} carries no version specifier")
    unsupported = sorted({operator for operator, _ in specifiers} - set(_COMPARISONS))
    if unsupported:
        raise PrepareReleaseError(
            f"the requirement {requirement!r} uses {', '.join(unsupported)}, which this check "
            "does not implement. Rewrite it with explicit bounds."
        )
    return specifiers


def _version_key(candidate: str) -> tuple[tuple[int, ...], int, int]:
    """Returns a sortable key for a plain `X.Y.Z` version with an optional pre-release.

    Trailing zeros are dropped so that `0.1` and `0.1.0` compare equal, and a
    pre-release sorts below the release it leads to.

    Raises:
        PrepareReleaseError: The version is not one this check can compare.
    """
    match = _VERSION_RE.match(candidate.strip())
    if match is None:
        raise PrepareReleaseError(
            f"version {candidate!r} is not a plain X.Y.Z with an optional aN/bN/rcN suffix; "
            "this check does not compare epochs, post or dev releases"
        )
    release = tuple(int(part) for part in match["release"].split("."))
    while len(release) > 1 and release[-1] == 0:
        release = release[:-1]
    if match["kind"] is None:
        return release, len(_PRE_RELEASE_ORDER), 0
    return release, _PRE_RELEASE_ORDER[match["kind"]], int(match["number"])


def _version_key_or_none(candidate: str) -> tuple[tuple[int, ...], int, int] | None:
    """`_version_key`, or None for a version shape this check cannot compare.

    An index lists whatever its publishers uploaded, including shapes this module
    refuses. One of those must not fail a lookup that is only asking whether some
    entry equals the floor.
    """
    try:
        return _version_key(candidate)
    except PrepareReleaseError:
        return None
