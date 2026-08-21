from uuid import UUID

from pytest_mock import MockerFixture

from lightly_studio.analytics import cohort, install_id
from lightly_studio.analytics.cohort import UserCohort
from lightly_studio.api import analytics_config


def test_get_analytics_config(mocker: MockerFixture) -> None:
    mocker.patch.object(analytics_config, "LIGHTLY_STUDIO_ANALYTICS_ENABLED", True)
    distinct_id = UUID("00000000-0000-4000-8000-000000000000")
    mocker.patch.object(install_id, "get_install_id", return_value=distinct_id)
    mocker.patch.object(cohort, "get_cohort", return_value=UserCohort.STAFF)

    config = analytics_config.get_analytics_config()

    assert config.enabled
    assert config.distinct_id == str(distinct_id)
    assert config.user_cohort == UserCohort.STAFF


def test_get_analytics_config__with_analytics_disabled(mocker: MockerFixture) -> None:
    """Opting out must leave no identity behind, on disk or in the response."""
    mocker.patch.object(analytics_config, "LIGHTLY_STUDIO_ANALYTICS_ENABLED", False)
    get_install_id = mocker.patch.object(install_id, "get_install_id")

    config = analytics_config.get_analytics_config()

    assert not config.enabled
    assert config.distinct_id is None
    assert config.user_cohort is None
    get_install_id.assert_not_called()
