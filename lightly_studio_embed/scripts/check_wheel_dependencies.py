"""Fails if the built wheel resolves anything heavy.

`lightly-studio-embed` is installed onto a customer's inference box, next to their own CUDA and
torch pins, so the dependency tree of the published wheel is the one property the package has to
keep. In a monorepo that is easy to break by accident, so it is asserted rather than reviewed.

Run it through `make check-wheel-dependencies`, which builds the wheel first.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Matched as substrings, so that variants such as duckdb-engine, torchvision or
# opencv-python-headless are caught too. `cuda` and `nvidia` cover the CUDA wheels, which can
# arrive without torch pulling them in.
FORBIDDEN_DEPENDENCIES = ("lightly-studio", "torch", "duckdb", "opencv", "cuda", "nvidia")

# The package's own name contains `lightly-studio`, so it is excluded from the matching or the
# check would report itself.
PACKAGE_NAME = "lightly-studio-embed"

_DISTRIBUTION_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+")


def main() -> int:
    """Resolves the wheel's dependency tree and reports anything forbidden in it.

    Returns:
        0 when the tree is clean, 1 otherwise.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--wheel-dir", type=Path, default=Path("dist"), help="Directory holding the built wheel."
    )
    parser.add_argument(
        "--python-version",
        default="3.9",
        help="Python version to resolve for, defaulting to the floor of `requires-python`.",
    )
    args = parser.parse_args()

    wheel = find_wheel(wheel_dir=args.wheel_dir)
    dependencies = resolve_dependencies(wheel=wheel, python_version=args.python_version)
    forbidden = find_forbidden(dependencies=dependencies)

    if forbidden:
        for dependency, pattern in forbidden:
            print(f"Error: the wheel resolves {dependency!r}, which matches {pattern!r}.")
        print("Resolved tree:")
        for dependency in dependencies:
            print(f"  {dependency}")
        return 1

    print(f"The wheel resolves none of: {', '.join(FORBIDDEN_DEPENDENCIES)}")
    return 0


def find_wheel(wheel_dir: Path) -> Path:
    """Returns the single wheel in `wheel_dir`.

    Args:
        wheel_dir: Directory that `make build` wrote the wheel to.

    Returns:
        Path to the wheel.

    Raises:
        SystemExit: If there is not exactly one wheel, since resolving a stale one alongside the
            current build would check the wrong artifact.
    """
    wheels = sorted(wheel_dir.glob("*.whl"))
    if len(wheels) != 1:
        raise SystemExit(f"expected exactly one wheel in {wheel_dir}, found {len(wheels)}")
    return wheels[0]


def resolve_dependencies(wheel: Path, python_version: str) -> list[str]:
    """Resolves the wheel's full transitive dependency tree without installing it.

    Args:
        wheel: The wheel to resolve.
        python_version: Python version to resolve for.

    Returns:
        The distribution names the wheel pulls in, excluding the wheel itself.
    """
    result = subprocess.run(
        [
            "uv",
            "pip",
            "compile",
            "-",
            "--python-version",
            python_version,
            "--no-header",
            "--no-annotate",
            "--quiet",
        ],
        input=f"{wheel.as_posix()}\n",
        capture_output=True,
        text=True,
        check=True,
    )
    names = (_distribution_name(line) for line in result.stdout.splitlines())
    return [name for name in names if name is not None and name != PACKAGE_NAME]


def find_forbidden(dependencies: list[str]) -> list[tuple[str, str]]:
    """Returns each resolved dependency that matches a forbidden pattern, with the pattern."""
    return [
        (dependency, pattern)
        for dependency in dependencies
        for pattern in FORBIDDEN_DEPENDENCIES
        if pattern in dependency
    ]


def _distribution_name(requirement: str) -> str | None:
    """Extracts the distribution name from a line of `uv pip compile` output.

    Args:
        requirement: One output line, such as `fastapi==0.128.8`, a comment, or the path of the
            wheel being resolved.

    Returns:
        The normalised distribution name, or None for a line that names no distribution.
    """
    requirement = requirement.strip()
    if not requirement or requirement.startswith("#") or "/" in requirement.split("@")[0]:
        return None
    match = _DISTRIBUTION_NAME_RE.match(requirement)
    if match is None:
        return None
    return match.group().lower().replace("_", "-")


if __name__ == "__main__":
    sys.exit(main())
