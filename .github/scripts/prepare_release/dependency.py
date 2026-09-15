"""Guard the requirement one workspace member declares on another.

uv resolves a workspace dependency from the workspace and drops the declared
specifier: `uv.lock` records the member with no `specifier` field, where every
registry dependency keeps one. So `uv lock`, `uv sync` and `uv lock --check` pass
whatever the requirement says, and the range that ships in the wheel is never
exercised. `assert_admits_version` exercises it.

This is the one module of the CLI that needs a third-party import, so cli.py
imports it from inside its handler rather than at the top: every other
subcommand stays runnable on whatever bare `python3` a runner or a laptop
provides (see version.py). The workflow step supplies `packaging` with
`uv run --with`.
"""

from __future__ import annotations

import re

from packaging.requirements import InvalidRequirement, Requirement
from packaging.version import InvalidVersion, Version

from prepare_release import version as version_module
from prepare_release.errors import PrepareReleaseError


def assert_admits_version(pyproject_text: str, dependency: str, dependency_version: str) -> None:
    """Fails if the requirement on `dependency` excludes the version it resolves to.

    Args:
        pyproject_text: The dependent package's pyproject.toml.
        dependency: The distribution name of the workspace dependency.
        dependency_version: The `[project]` version of that workspace member.

    Raises:
        PrepareReleaseError: There is no such requirement, it carries no
            specifier, or it does not admit `dependency_version`.
    """
    requirement = read_requirement(pyproject_text=pyproject_text, distribution=dependency)
    if not admits(requirement=requirement, candidate=dependency_version):
        raise PrepareReleaseError(
            f"the workspace builds and tests against {dependency} {dependency_version}, but "
            f"the requirement {requirement!r} excludes it. The wheel would declare a range "
            "that this repository never ran. Widen the requirement, or release the "
            "dependency at a version the range admits."
        )


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


def admits(requirement: str, candidate: str) -> bool:
    """Whether the specifier set of `requirement` accepts `candidate`.

    Raises:
        PrepareReleaseError: The requirement carries no specifier, or it or
            `candidate` is not valid PEP 508 / PEP 440. An unbounded requirement
            on a package released from this repository is a mistake: it would
            resolve to anything ever published.
    """
    try:
        specifier = Requirement(requirement).specifier
    except InvalidRequirement as error:
        raise PrepareReleaseError(
            f"the requirement {requirement!r} is not valid PEP 508: {error}"
        ) from error
    if not specifier:
        raise PrepareReleaseError(f"the requirement {requirement!r} carries no version specifier")
    try:
        version = Version(candidate)
    except InvalidVersion as error:
        # `SpecifierSet.contains` answers False for a string it cannot parse,
        # which would be reported as an excluded version rather than a bad one.
        raise PrepareReleaseError(f"version {candidate!r} is not valid PEP 440: {error}") from error
    # A pre-release in the tree is weighed against the declared bounds rather
    # than excluded out of hand, which is what `packaging` does by default.
    return specifier.contains(version, prereleases=True)
