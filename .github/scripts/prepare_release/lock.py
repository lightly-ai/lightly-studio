"""Guard against `uv sync` widening the `uv.lock` diff beyond the version bump.

`uv sync` on a CI runner can resolve transitive dependencies differently
from whoever last locked (different Python patch, platform, or registry
state), producing a diff wider than the version bump. That doesn't
endanger the published wheel - dependency metadata comes from
`pyproject.toml`, not the lock - but it makes the release PR unreviewable
and drifts the dev/CI environment away from what was last validated.
"""

from __future__ import annotations

import difflib
import re

from prepare_release.errors import PrepareReleaseError

_LOCK_PACKAGE_SPLIT_RE = re.compile(r"(?=^\[\[package\]\]$)", re.MULTILINE)
_LOCK_PACKAGE_NAME_RE = re.compile(r'^name = "(?P<name>[^"]+)"$', re.MULTILINE)


def assert_lock_diff_narrow(before_text: str, after_text: str, package: str) -> None:
    """Fails if `uv sync` changed more than `package`'s version line."""
    before_blocks = _parse_lock_blocks(before_text)
    after_blocks = _parse_lock_blocks(after_text)

    unexpected = sorted(
        name or "<lockfile header>"
        for name in set(before_blocks.keys()) | set(after_blocks.keys())
        if name != package and before_blocks.get(name) != after_blocks.get(name)
    )
    if unexpected:
        raise PrepareReleaseError(
            "uv sync changed packages beyond the version bump: " + ", ".join(unexpected)
        )

    before_pkg_blocks = before_blocks.get(package)
    after_pkg_blocks = after_blocks.get(package)
    if not before_pkg_blocks or not after_pkg_blocks:
        raise PrepareReleaseError(f"package {package!r} not found in uv.lock before/after uv sync")
    if len(before_pkg_blocks) != len(after_pkg_blocks):
        raise PrepareReleaseError(
            f"uv sync changed the number of {package!r} blocks in uv.lock "
            f"({len(before_pkg_blocks)} -> {len(after_pkg_blocks)})"
        )

    for before_pkg, after_pkg in zip(before_pkg_blocks, after_pkg_blocks):
        diff = difflib.unified_diff(before_pkg.splitlines(), after_pkg.splitlines(), lineterm="")
        changed_lines = [
            line for line in diff if line[:1] in "+-" and line[:3] not in ("+++", "---")
        ]
        if any(not re.match(r'^[+-]version = "', line) for line in changed_lines):
            raise PrepareReleaseError(
                f"uv.lock diff for {package!r} touches more than its version line:\n"
                + "\n".join(changed_lines)
            )


def _parse_lock_blocks(uv_lock_text: str) -> dict[str, list[str]]:
    """Splits a `uv.lock`'s text into per-package blocks, keyed by name.

    `uv`'s universal resolution can emit several `[[package]]` blocks for
    the same name - one per platform/Python-version marker, or per
    resolution fork - so each name maps to the list of its blocks in file
    order rather than a single block. The lockfile header (everything
    before the first `[[package]]`) is kept under the empty-string key so
    it participates in the same diff check.
    """
    chunks = _LOCK_PACKAGE_SPLIT_RE.split(uv_lock_text)
    blocks: dict[str, list[str]] = {"": [chunks[0]]}
    for chunk in chunks[1:]:
        match = _LOCK_PACKAGE_NAME_RE.search(chunk)
        if match is None:
            raise PrepareReleaseError("a uv.lock [[package]] block has no `name` field")
        blocks.setdefault(match.group("name"), []).append(chunk)
    return blocks
