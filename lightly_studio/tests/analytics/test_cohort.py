from __future__ import annotations

import json
from importlib import metadata
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from lightly_studio.analytics import cohort
from lightly_studio.analytics.cohort import UserCohort


# Signals are (marker file present, LIGHTLY_STUDIO_INTERNAL, CI variable, installed from source).
@pytest.mark.parametrize(
    ("signals", "expected"),
    [
        # Either deliberate signal marks the machine, and both win over a CI variable.
        ((True, False, "true", False), UserCohort.STAFF),
        ((False, True, "true", False), UserCohort.STAFF),
        ((False, False, "true", False), UserCohort.CI),
        # An emptied variable is how CI providers unset it.
        ((False, False, "", True), UserCohort.SOURCE_BUILD),
        # A tool or a developer using CI as a switch must not turn a real user into a CI run.
        ((False, False, "false", True), UserCohort.SOURCE_BUILD),
        ((False, False, "0", False), UserCohort.USER),
        ((False, False, "", False), UserCohort.USER),
        # Providers that name themselves rather than spelling out a boolean.
        ((False, False, "drone", False), UserCohort.CI),
    ],
)
def test_get_cohort(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
    signals: tuple[bool, bool, str, bool],
    expected: UserCohort,
) -> None:
    marked, internal_env, ci, is_source_build = signals
    marker_path = tmp_path / "internal"
    if marked:
        marker_path.touch()
    monkeypatch.setenv(cohort._CI_ENV_VAR, ci)
    mocker.patch.object(cohort, "LIGHTLY_STUDIO_INTERNAL", internal_env)
    mocker.patch.object(cohort, "_is_source_build", return_value=is_source_build)

    assert cohort.get_cohort(marker_path=marker_path) == expected


@pytest.mark.parametrize(
    ("direct_url", "expected"),
    [
        (json.dumps({"url": "file:///repo", "dir_info": {"editable": True}}), True),
        # A wheel from PyPI records no direct URL at all.
        (None, False),
        (json.dumps({"url": "https://example.com/pkg.whl"}), False),
        # Malformed records must not raise, nor match the wrong thing.
        ("null", False),
        ('"dir_info"', False),
        ("not json", False),
    ],
)
def test_is_source_build(mocker: MockerFixture, direct_url: str | None, expected: bool) -> None:
    distribution = mocker.MagicMock()
    distribution.read_text.return_value = direct_url
    mocker.patch.object(metadata, "distribution", return_value=distribution)

    assert cohort._is_source_build() == expected


def test_is_source_build__without_the_package_installed(mocker: MockerFixture) -> None:
    mocker.patch.object(metadata, "distribution", side_effect=metadata.PackageNotFoundError)

    assert cohort._is_source_build()


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1", True),
        ("true", True),
        ("TRUE", True),
        (" yes ", True),
        # Providers that name themselves rather than spelling out a boolean.
        ("drone", True),
        ("woodpecker", True),
        # Values a tool or a developer sets to switch the variable off.
        ("0", False),
        ("false", False),
        ("FALSE", False),
        ("no", False),
        ("off", False),
        ("n", False),
        ("", False),
        ("   ", False),
        (None, False),
    ],
)
def test_is_ci(monkeypatch: pytest.MonkeyPatch, value: str | None, expected: bool) -> None:
    if value is None:
        monkeypatch.delenv(cohort._CI_ENV_VAR, raising=False)
    else:
        monkeypatch.setenv(cohort._CI_ENV_VAR, value)

    assert cohort._is_ci() == expected
