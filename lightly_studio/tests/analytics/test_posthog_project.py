"""Tests for the PostHog project selection."""

import pytest
from pytest_mock import MockerFixture

from lightly_studio.analytics import posthog_project
from lightly_studio.analytics.cohort import UserCohort


@pytest.fixture(autouse=True)
def _no_key_override(mocker: MockerFixture) -> None:
    """Undo the suite-wide empty override, which short-circuits every case below."""
    mocker.patch.object(posthog_project, "LIGHTLY_STUDIO_POSTHOG_KEY", None)


def test_get_project_key__user_reports_to_production() -> None:
    assert posthog_project.get_project_key(UserCohort.USER) == posthog_project.PROD_PROJECT_KEY


def test_get_project_key__staff_reports_to_dev() -> None:
    assert posthog_project.get_project_key(UserCohort.STAFF) == posthog_project.DEV_PROJECT_KEY


def test_get_project_key__ci_reports_to_dev() -> None:
    assert posthog_project.get_project_key(UserCohort.CI) == posthog_project.DEV_PROJECT_KEY


def test_get_project_key__source_build_reports_to_dev() -> None:
    assert (
        posthog_project.get_project_key(UserCohort.SOURCE_BUILD) == posthog_project.DEV_PROJECT_KEY
    )


def test_get_project_key__override_wins(mocker: MockerFixture) -> None:
    mocker.patch.object(posthog_project, "LIGHTLY_STUDIO_POSTHOG_KEY", "phc_override")

    assert posthog_project.get_project_key(UserCohort.USER) == "phc_override"


def test_get_project_key__empty_override_disables(mocker: MockerFixture) -> None:
    mocker.patch.object(posthog_project, "LIGHTLY_STUDIO_POSTHOG_KEY", "")

    assert posthog_project.get_project_key(UserCohort.USER) == ""


def test_get_project_key__projects_differ() -> None:
    # A change that collapsed the two projects would otherwise go unnoticed.
    assert posthog_project.DEV_PROJECT_KEY != posthog_project.PROD_PROJECT_KEY
