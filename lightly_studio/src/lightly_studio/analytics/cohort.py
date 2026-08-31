"""Cohort a running installation belongs to.

Internal usage has to be separable from real users, otherwise a handful of devs and CI runs
dominate the product signal while the user base is small.
"""

from __future__ import annotations

import json
import os
from enum import Enum
from importlib import metadata
from pathlib import Path

from lightly_studio.dataset.env import (
    LIGHTLY_STUDIO_INTERNAL,
    LIGHTLY_STUDIO_MODEL_CACHE_DIR,
)

# Shares the directory with the installation ID, so marking a machine survives recreating the
# virtualenv. LIGHTLY_STUDIO_INTERNAL alone is forgotten when it matters most, on a fresh
# container or a new laptop.
INTERNAL_MARKER_PATH: Path = LIGHTLY_STUDIO_MODEL_CACHE_DIR / "internal"

# Set by every CI provider we run on, GitHub Actions included. A build matrix otherwise looks like
# one very active user.
_CI_ENV_VAR = "CI"

# Values of the CI variable that read as not CI. `CI=false` and `CI=0` mean the opposite of what a
# non-empty check reads them as. Anything else counts as CI, because providers put their own name
# in the variable, `CI=drone` among them.
_FALSE_VALUES = frozenset({"", "0", "false", "no", "off", "f", "n"})


class UserCohort(str, Enum):
    """Who is behind the events of one installation.

    Attributes:
        STAFF: A Lightly dev or staff member, opted in explicitly.
        CI: An automated build, not a person.
        SOURCE_BUILD: Installed from a checkout, so staff who did not opt in, or a contributor.
        USER: Everyone else, a released package on someone else's machine.
    """

    STAFF = "staff"
    CI = "ci"
    SOURCE_BUILD = "source_build"
    USER = "user"


def get_cohort(marker_path: Path = INTERNAL_MARKER_PATH) -> UserCohort:
    """Get the cohort of this installation.

    Args:
        marker_path: File whose presence marks the machine as internal.

    Returns:
        The cohort. `USER` whenever nothing indicates otherwise, so a misdetection loses internal
        traffic from the internal metrics rather than polluting the product metrics.
    """
    # The deliberate signal wins: a marked machine stays internal even when a tool exports CI in
    # the shell.
    if LIGHTLY_STUDIO_INTERNAL or marker_path.exists():
        return UserCohort.STAFF
    if _is_ci():
        return UserCohort.CI
    if _is_source_build():
        return UserCohort.SOURCE_BUILD
    return UserCohort.USER


def _is_source_build() -> bool:
    """Whether the installed package was built from a local checkout rather than a release.

    A `dir_info` entry in the PEP 610 `direct_url.json` record means the install came from a
    directory on disk, covering both `pip install -e .` and a plain install from a checkout.
    """
    try:
        direct_url = metadata.distribution("lightly-studio").read_text("direct_url.json")
    except metadata.PackageNotFoundError:
        # Running straight from a checkout, without the package installed at all.
        return True

    if direct_url is None:
        return False
    try:
        record = json.loads(direct_url)
    except json.JSONDecodeError:
        return False
    # A record that is not an object is malformed. `in` would raise on null or a number, and match
    # the wrong thing on a string or an array.
    return isinstance(record, dict) and "dir_info" in record


def _is_ci() -> bool:
    """Whether an automated build is running, per the variable every provider we run on sets."""
    return os.environ.get(_CI_ENV_VAR, "").strip().lower() not in _FALSE_VALUES
