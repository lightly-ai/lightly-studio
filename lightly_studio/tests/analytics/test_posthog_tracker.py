import logging
from collections.abc import Generator
from uuid import UUID

import pytest
from pytest_mock import MockerFixture

from lightly_studio.analytics import install_id, posthog_tracker
from lightly_studio.analytics.posthog_tracker import PostHogTracker

INSTALL_ID = UUID("0199f1a2-b775-76b8-9b09-c2fd260c67c1")


@pytest.fixture(autouse=True)
def restore_logger_levels() -> Generator[None, None, None]:
    """Keep the logger levels these tests change out of the rest of the suite."""
    levels = {name: logging.getLogger(name).level for name in posthog_tracker._NOISY_LOGGERS}
    yield
    for name, level in levels.items():
        logging.getLogger(name).setLevel(level)


class TestPostHogTracker:
    def test_init(self, mocker: MockerFixture) -> None:
        mocker.patch.object(install_id, "get_install_id", return_value=INSTALL_ID)
        client = mocker.patch.object(posthog_tracker, "Posthog")

        PostHogTracker(project_api_key="phc_test")

        client.assert_called_once_with(
            project_api_key="phc_test",
            host=posthog_tracker.POSTHOG_HOST,
            max_retries=posthog_tracker.MAX_RETRIES,
            timeout=posthog_tracker.REQUEST_TIMEOUT_SECONDS,
        )

    def test_init__silences_delivery_logging(self, mocker: MockerFixture) -> None:
        """An unreachable analytics endpoint must not print anything to the user's terminal."""
        mocker.patch.object(install_id, "get_install_id", return_value=INSTALL_ID)

        def build_client(**_kwargs: object) -> object:
            # The real client raises its own logger level while being constructed, which is why
            # the tracker has to silence it afterwards rather than before.
            logging.getLogger("posthog").setLevel(logging.WARNING)
            return mocker.MagicMock()

        mocker.patch.object(posthog_tracker, "Posthog", side_effect=build_client)

        PostHogTracker(project_api_key="phc_test")

        for name in posthog_tracker._NOISY_LOGGERS:
            assert logging.getLogger(name).level == logging.CRITICAL

    def test_track(self, mocker: MockerFixture) -> None:
        mocker.patch.object(install_id, "get_install_id", return_value=INSTALL_ID)
        mocker.patch.object(posthog_tracker, "_common_properties", return_value={"os": "Linux"})
        client = mocker.patch.object(posthog_tracker, "Posthog").return_value

        PostHogTracker(project_api_key="phc_test").track(
            event="app_launched", properties={"launch_source": "quickstart"}
        )

        client.capture.assert_called_once_with(
            event="app_launched",
            distinct_id=str(INSTALL_ID),
            properties={"os": "Linux", "launch_source": "quickstart"},
        )

    def test_shutdown(self, mocker: MockerFixture) -> None:
        mocker.patch.object(install_id, "get_install_id", return_value=INSTALL_ID)
        client = mocker.patch.object(posthog_tracker, "Posthog").return_value

        PostHogTracker(project_api_key="phc_test").shutdown()

        client.shutdown.assert_called_once_with()


def test_common_properties() -> None:
    properties = posthog_tracker._common_properties()

    assert set(properties) == {"lightly_studio_version", "python_version", "os"}
    assert all(properties.values())
