"""Tests the dependency metadata that ships in the lightly-studio wheel."""

from __future__ import annotations

import os
import subprocess
import sys
from importlib import metadata

from packaging.requirements import Requirement

WORKSPACE_DEPENDENCY = "lightly-studio-serve"
JOBS_DEPENDENCY = "hatchet-sdk"
# Each of these modules must import when the jobs extra is not installed.
MODULES_WITHOUT_JOBS_EXTRA = ("lightly_studio", "lightly_studio.api.app")


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


def test_jobs_extra__pins_hatchet_sdk_exactly() -> None:
    requirement = _read_requirement(distribution=JOBS_DEPENDENCY)
    assert requirement.marker is not None
    assert requirement.marker.evaluate({"extra": "jobs"})
    assert not requirement.marker.evaluate({"extra": ""})
    specifiers = list(requirement.specifier)
    assert len(specifiers) == 1
    assert specifiers[0].operator == "=="


def test_import__without_jobs_extra() -> None:
    """The app imports when the jobs extra is missing, also if it is installed here."""
    # A None entry in sys.modules makes every import of the module fail.
    imports = "; ".join(f"import {module}" for module in MODULES_WITHOUT_JOBS_EXTRA)
    code = f"import sys; sys.modules['hatchet_sdk'] = None; {imports}"
    # The analytics fixture of the suite does not apply to the new process. Without this, the
    # import starts a tracker that reports a failed import to PostHog.
    environment = {**os.environ, "LIGHTLY_STUDIO_ANALYTICS_ENABLED": "false"}
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )
    assert result.returncode == 0, result.stderr


def _read_requirement(distribution: str) -> Requirement:
    requirements = [Requirement(text) for text in metadata.requires("lightly-studio") or ()]
    matches = [requirement for requirement in requirements if requirement.name == distribution]
    assert len(matches) == 1, f"expected one requirement on {distribution}, found {len(matches)}"
    return matches[0]
