"""Settings of background jobs that are derived from the environment."""

from __future__ import annotations

import os

from lightly_studio.dataset import env

# The SDK reads the engine token from this variable. It is not copied into the studio settings.
HATCHET_CLIENT_TOKEN_VARIABLE = "HATCHET_CLIENT_TOKEN"

# How long a run waits for a worker before it fails, per worker launcher. A launched worker
# needs more time to start.
DEFAULT_SCHEDULE_TIMEOUT_SECONDS = {"none": 300, "ecs": 900}


def jobs_configured() -> bool:
    """Returns True if the signing secret and the engine token are both set."""
    signing_secret = env.LIGHTLY_STUDIO_JOBS_SIGNING_SECRET
    engine_token = os.environ.get(HATCHET_CLIENT_TOKEN_VARIABLE)
    return bool(signing_secret) and bool(engine_token)


def schedule_timeout_seconds() -> int:
    """Returns how long a run waits for a worker before it fails.

    Raises:
        ValueError: If the timeout is not set and the worker launcher is unknown.
    """
    if env.LIGHTLY_STUDIO_JOBS_SCHEDULE_TIMEOUT_SECONDS is not None:
        return env.LIGHTLY_STUDIO_JOBS_SCHEDULE_TIMEOUT_SECONDS
    launcher = env.LIGHTLY_STUDIO_JOBS_WORKER_LAUNCHER
    if launcher not in DEFAULT_SCHEDULE_TIMEOUT_SECONDS:
        raise ValueError(f"Unknown jobs worker launcher: {launcher!r}.")
    return DEFAULT_SCHEDULE_TIMEOUT_SECONDS[launcher]
