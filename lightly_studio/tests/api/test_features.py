from pytest_mock import MockerFixture

from lightly_studio.api import features


def test_get_active_features(mocker: MockerFixture) -> None:
    mocker.patch.object(features, "LIGHTLY_STUDIO_ANALYTICS_ENABLED", True)
    mocker.patch.object(features, "LIGHTLY_STUDIO_POINT_CLOUD_ENABLED", False)

    assert features._get_active_features() == [features.ANALYTICS_FEATURE]


def test_get_active_features__with_analytics_disabled(mocker: MockerFixture) -> None:
    """Opting out must also stop the GUI from starting PostHog."""
    mocker.patch.object(features, "LIGHTLY_STUDIO_ANALYTICS_ENABLED", False)
    mocker.patch.object(features, "LIGHTLY_STUDIO_POINT_CLOUD_ENABLED", False)

    assert features._get_active_features() == []


def test_get_active_features__with_point_cloud_rendering_enabled(mocker: MockerFixture) -> None:
    mocker.patch.object(features, "LIGHTLY_STUDIO_ANALYTICS_ENABLED", False)
    mocker.patch.object(features, "LIGHTLY_STUDIO_POINT_CLOUD_ENABLED", True)

    assert features._get_active_features() == [features.POINT_CLOUD_RENDERING_FEATURE]


def test_get_active_features__with_point_cloud_rendering_disabled_by_default(
    mocker: MockerFixture,
) -> None:
    """Disabling the flag must not affect the existing (non-workspace) sample detail view."""
    mocker.patch.object(features, "LIGHTLY_STUDIO_ANALYTICS_ENABLED", True)
    mocker.patch.object(features, "LIGHTLY_STUDIO_POINT_CLOUD_ENABLED", False)

    assert features.POINT_CLOUD_RENDERING_FEATURE not in features._get_active_features()
