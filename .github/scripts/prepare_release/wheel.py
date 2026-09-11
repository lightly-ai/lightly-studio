"""Check what a built wheel actually pulls in, before it can be published.

`lightly-studio-embed` exists to be installed next to a customer's own CUDA and torch
pins, so the one thing that must stay true of it is that it stays light. A
`pyproject.toml` review cannot establish that: the offending dependency arrives one
level down. This installs the wheel into a throwaway environment and looks at what
came with it.
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from collections.abc import Sequence
from pathlib import Path

from prepare_release.errors import PrepareReleaseError
from prepare_release.packages import Package

# PEP 503 name normalization, so `nvidia_cublas_cu12` and `NVIDIA-cuBLAS-cu12` are the
# same name to match against.
_NAME_SEPARATOR_RE = re.compile(r"[-_.]+")


def check_wheel_dependencies(dist_dir: Path, package: Package) -> None:
    """Resolves the wheel in `dist_dir` and fails on a forbidden dependency.

    Raises:
        PrepareReleaseError: `dist_dir` holds no single wheel, or the resolved tree
            contains a forbidden name.
    """
    wheel = find_wheel(dist_dir)
    with tempfile.TemporaryDirectory() as temp_dir:
        environment = Path(temp_dir) / "venv"
        _uv("venv", str(environment))
        _uv("pip", "install", "--python", str(environment), str(wheel))
        listing = _uv("pip", "list", "--python", str(environment), "--format", "json")
    assert_no_forbidden_dependencies(installed=parse_installed_names(listing), package=package)


def find_wheel(dist_dir: Path) -> Path:
    """Returns the one wheel in `dist_dir`.

    Raises:
        PrepareReleaseError: There is not exactly one wheel there. More than one means
            an earlier build was not cleaned away, and checking the wrong one is worse
            than not checking.
    """
    wheels = sorted(dist_dir.glob("*.whl"))
    if len(wheels) != 1:
        raise PrepareReleaseError(f"expected exactly one wheel in {dist_dir}, found {len(wheels)}")
    return wheels[0]


def parse_installed_names(pip_list_json: str) -> list[str]:
    """Returns the distribution names in `uv pip list --format json` output.

    Raises:
        PrepareReleaseError: The output is not the expected list of named entries.
    """
    try:
        entries = json.loads(pip_list_json)
        return [str(entry["name"]) for entry in entries]
    except (json.JSONDecodeError, TypeError, KeyError) as error:
        raise PrepareReleaseError(f"could not read the installed package list: {error}") from error


def assert_no_forbidden_dependencies(installed: Sequence[str], package: Package) -> None:
    """Fails if any installed name contains one of `package.forbidden_dependencies`.

    The package itself is skipped: `lightly-studio-embed` carries the `lightly-studio`
    substring that it forbids of everything else.

    Raises:
        PrepareReleaseError: A forbidden name is installed.
    """
    own_name = normalize_name(package.distribution)
    # Both sides are normalized: a pattern written `opencv_python` or `NVIDIA` would
    # otherwise never match a normalized name, and this guard would fail open.
    patterns = [normalize_name(pattern) for pattern in package.forbidden_dependencies]
    offenders = sorted(
        name
        for name in installed
        if normalize_name(name) != own_name
        and any(pattern in normalize_name(name) for pattern in patterns)
    )
    if offenders:
        raise PrepareReleaseError(
            f"the {package.distribution} wheel resolves to dependencies it must not have: "
            + ", ".join(offenders)
        )


def normalize_name(name: str) -> str:
    """Returns the PEP 503 normalized form of a distribution name."""
    return _NAME_SEPARATOR_RE.sub("-", name).lower()


def _uv(*args: str) -> str:
    """Runs `uv` with `args` and returns its standard output.

    Raises:
        PrepareReleaseError: `uv` is missing or exited non-zero.
    """
    try:
        completed = subprocess.run(["uv", *args], capture_output=True, text=True, check=True)
    except FileNotFoundError as error:
        raise PrepareReleaseError("uv is not installed") from error
    except subprocess.CalledProcessError as error:
        raise PrepareReleaseError(f"`uv {' '.join(args)}` failed:\n{error.stderr}") from error
    return completed.stdout
