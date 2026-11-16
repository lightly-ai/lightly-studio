from __future__ import annotations

import importlib
import os
from collections.abc import Iterator

import pytest
from pytest_mock import MockerFixture

from lightly_studio.dataset import env
from lightly_studio.jobs import settings

JOBS_VARIABLE_PREFIX = "LIGHTLY_STUDIO_JOBS_"


@pytest.fixture
def jobs_environment(monkeypatch: pytest.MonkeyPatch) -> Iterator[pytest.MonkeyPatch]:
    """Removes the jobs variables from the environment and restores the env module after the test.

    The env module reads the variables once on import. A test sets them and reloads the module.
    """
    for key in list(os.environ):
        if key.startswith(JOBS_VARIABLE_PREFIX):
            monkeypatch.delenv(key)
    yield monkeypatch
    # Restore the environment before the reload. Else the reload reads the patched values.
    monkeypatch.undo()
    importlib.reload(env)


@pytest.mark.usefixtures("jobs_environment")
def test_jobs_env__defaults() -> None:
    importlib.reload(env)

    assert env.LIGHTLY_STUDIO_JOBS_SIGNING_SECRET is None
    assert env.LIGHTLY_STUDIO_JOBS_TENANT == "default"
    assert env.LIGHTLY_STUDIO_JOBS_WORKER_LAUNCHER == "none"
    assert env.LIGHTLY_STUDIO_JOBS_SECRET_PROVIDER == "env"
    assert env.LIGHTLY_STUDIO_JOBS_WORKER_JOB_ID is None
    assert env.LIGHTLY_STUDIO_JOBS_SCHEDULE_TIMEOUT_SECONDS is None


def test_jobs_env__read_from_environment(jobs_environment: pytest.MonkeyPatch) -> None:
    jobs_environment.setenv("LIGHTLY_STUDIO_JOBS_SIGNING_SECRET", "secret")
    jobs_environment.setenv("LIGHTLY_STUDIO_JOBS_TENANT", "acme")
    jobs_environment.setenv("LIGHTLY_STUDIO_JOBS_WORKER_LAUNCHER", "ecs")
    jobs_environment.setenv("LIGHTLY_STUDIO_JOBS_SECRET_PROVIDER", "ssm")
    jobs_environment.setenv("LIGHTLY_STUDIO_JOBS_WORKER_JOB_ID", "job-1")
    jobs_environment.setenv("LIGHTLY_STUDIO_JOBS_SCHEDULE_TIMEOUT_SECONDS", "42")
    importlib.reload(env)

    assert env.LIGHTLY_STUDIO_JOBS_SIGNING_SECRET == "secret"
    assert env.LIGHTLY_STUDIO_JOBS_TENANT == "acme"
    assert env.LIGHTLY_STUDIO_JOBS_WORKER_LAUNCHER == "ecs"
    assert env.LIGHTLY_STUDIO_JOBS_SECRET_PROVIDER == "ssm"
    assert env.LIGHTLY_STUDIO_JOBS_WORKER_JOB_ID == "job-1"
    assert env.LIGHTLY_STUDIO_JOBS_SCHEDULE_TIMEOUT_SECONDS == 42


@pytest.mark.parametrize(
    ("signing_secret", "engine_token", "expected"),
    [
        (None, None, False),
        ("secret", None, False),
        (None, "token", False),
        ("", "token", False),
        ("secret", "", False),
        ("secret", "token", True),
    ],
)
def test_jobs_configured(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    signing_secret: str | None,
    engine_token: str | None,
    expected: bool,
) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_JOBS_SIGNING_SECRET", signing_secret)
    if engine_token is None:
        monkeypatch.delenv("HATCHET_CLIENT_TOKEN", raising=False)
    else:
        monkeypatch.setenv("HATCHET_CLIENT_TOKEN", engine_token)

    assert settings.jobs_configured() is expected


@pytest.mark.parametrize(("launcher", "expected"), [("none", 300), ("ecs", 900)])
def test_schedule_timeout_seconds__default_per_launcher(
    mocker: MockerFixture, launcher: str, expected: int
) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_JOBS_SCHEDULE_TIMEOUT_SECONDS", None)
    mocker.patch.object(env, "LIGHTLY_STUDIO_JOBS_WORKER_LAUNCHER", launcher)

    assert settings.schedule_timeout_seconds() == expected


@pytest.mark.parametrize("launcher", ["none", "ecs"])
def test_schedule_timeout_seconds__set(mocker: MockerFixture, launcher: str) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_JOBS_SCHEDULE_TIMEOUT_SECONDS", 42)
    mocker.patch.object(env, "LIGHTLY_STUDIO_JOBS_WORKER_LAUNCHER", launcher)

    assert settings.schedule_timeout_seconds() == 42


def test_schedule_timeout_seconds__unknown_launcher(mocker: MockerFixture) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_JOBS_SCHEDULE_TIMEOUT_SECONDS", None)
    mocker.patch.object(env, "LIGHTLY_STUDIO_JOBS_WORKER_LAUNCHER", "esc")

    with pytest.raises(ValueError, match=r"Unknown jobs worker launcher: 'esc'"):
        settings.schedule_timeout_seconds()
