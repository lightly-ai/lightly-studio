"""Tests the dependency metadata that ships in the lightly-studio wheel."""

from __future__ import annotations

from importlib import metadata

from packaging.requirements import Requirement

WORKSPACE_DEPENDENCY = "lightly-studio-serve"


def test_workspace_dependency__requirement_admits_the_installed_version() -> None:
    """Nothing else exercises this range: uv drops a workspace dependency's specifier."""
    requirement = _read_requirement(distribution=WORKSPACE_DEPENDENCY)
    installed = metadata.version(WORKSPACE_DEPENDENCY)
    # A pre-release in the workspace is weighed against the bounds, not excluded out of hand.
    assert requirement.specifier.contains(installed, prereleases=True), (
        f"lightly-studio requires {requirement}, which excludes the {WORKSPACE_DEPENDENCY} "
        f"{installed} this workspace builds and tests against. Widen the requirement, or "
        f"release {WORKSPACE_DEPENDENCY} at a version the range admits."
    )


def _read_requirement(distribution: str) -> Requirement:
    requirements = [Requirement(text) for text in metadata.requires("lightly-studio") or ()]
    matches = [requirement for requirement in requirements if requirement.name == distribution]
    assert len(matches) == 1, f"expected one requirement on {distribution}, found {len(matches)}"
    return matches[0]
