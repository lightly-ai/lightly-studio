from pytest_mock import MockerFixture

from lightly_studio.api import features


def test_get_active_features(mocker: MockerFixture) -> None:
    mocker.patch.object(features, "LIGHTLY_STUDIO_ANALYTICS_ENABLED", True)

    assert features._get_active_features() == [features.ANALYTICS_FEATURE]


def test_get_active_features__with_analytics_disabled(mocker: MockerFixture) -> None:
    """Opting out must also stop the GUI from starting PostHog."""
    mocker.patch.object(features, "LIGHTLY_STUDIO_ANALYTICS_ENABLED", False)

    assert features._get_active_features() == []
