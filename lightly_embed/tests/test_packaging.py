"""Asserts the dependency floor of the published wheel.

`lightly-embed` is installed onto a customer's inference box, next to their own CUDA and torch
pins, so its dependency set is the one property the package has to keep. This checks what the
distribution metadata declares; the unit test workflow additionally resolves the built wheel's
full transitive tree and asserts that nothing heavy appears in it.
"""

import re
from importlib import metadata

EXPECTED_DEPENDENCIES = {"fastapi", "pydantic", "uvicorn"}

_DISTRIBUTION_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+")


def test_requires() -> None:
    requires = metadata.requires("lightly-embed")
    assert requires is not None
    assert {_distribution_name(r) for r in requires} == EXPECTED_DEPENDENCIES


def _distribution_name(requirement: str) -> str:
    """Extracts the distribution name from a requirement such as `fastapi>=0.115.5`."""
    match = _DISTRIBUTION_NAME_RE.match(requirement)
    assert match is not None
    return match.group().lower().replace("_", "-")
