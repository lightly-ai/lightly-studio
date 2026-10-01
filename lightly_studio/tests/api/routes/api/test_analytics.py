"""Tests for the analytics API route."""

from uuid import UUID

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from lightly_studio.analytics import cohort, install_id, posthog_project
from lightly_studio.analytics.cohort import UserCohort
from lightly_studio.api.routes.api import analytics
from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND, HTTP_STATUS_OK

INSTALL_ID = UUID("0199f1a2-b775-76b8-9b09-c2fd260c67c1")


def test_get_analytics_config(test_client: TestClient, mocker: MockerFixture) -> None:
    mocker.patch.object(analytics, "LIGHTLY_STUDIO_ANALYTICS_ENABLED", True)
    mocker.patch.object(posthog_project, "LIGHTLY_STUDIO_POSTHOG_KEY", None)
    mocker.patch.object(install_id, "get_install_id", return_value=INSTALL_ID)
    mocker.patch.object(cohort, "get_cohort", return_value=UserCohort.USER)

    response = test_client.get("/api/analytics/config")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {
        "install_id": str(INSTALL_ID),
        "posthog_key": posthog_project.PROD_PROJECT_KEY,
        "posthog_host": "https://eu.i.posthog.com",
    }


def test_get_analytics_config__a_source_build_reports_to_dev(
    test_client: TestClient, mocker: MockerFixture
) -> None:
    """The GUI has to land in the project the cohort picks, not the production one."""
    mocker.patch.object(analytics, "LIGHTLY_STUDIO_ANALYTICS_ENABLED", True)
    mocker.patch.object(posthog_project, "LIGHTLY_STUDIO_POSTHOG_KEY", None)
    mocker.patch.object(install_id, "get_install_id", return_value=INSTALL_ID)
    mocker.patch.object(cohort, "get_cohort", return_value=UserCohort.SOURCE_BUILD)

    response = test_client.get("/api/analytics/config")

    assert response.json()["posthog_key"] == posthog_project.DEV_PROJECT_KEY


def test_get_analytics_config__returns_not_found_when_analytics_disabled(
    test_client: TestClient, mocker: MockerFixture
) -> None:
    """Opting out must leave no install id on disk, so the endpoint refuses to create one."""
    mocker.patch.object(analytics, "LIGHTLY_STUDIO_ANALYTICS_ENABLED", False)
    get_install_id = mocker.patch.object(install_id, "get_install_id")

    response = test_client.get("/api/analytics/config")

    assert response.status_code == HTTP_STATUS_NOT_FOUND
    get_install_id.assert_not_called()
