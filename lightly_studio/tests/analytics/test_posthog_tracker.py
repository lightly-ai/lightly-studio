import logging
from collections.abc import Generator
from uuid import UUID

import pytest
from pytest_mock import MockerFixture

from lightly_studio.analytics import install_id, posthog_tracker
from lightly_studio.analytics.posthog_tracker import PostHogTracker

INSTALL_ID = UUID("0199f1a2-b775-76b8-9b09-c2fd260c67c1")


class RecordingHandler(logging.Handler):
    """Stands in for the handler that would write to the user's terminal."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture(autouse=True)
def restore_logger_state() -> Generator[None, None, None]:
    """Keep the logger changes these tests make out of the rest of the suite."""
    loggers = [logging.getLogger(name) for name in posthog_tracker._NOISY_LOGGERS]
    saved = [(logger, logger.level, logger.propagate, list(logger.handlers)) for logger in loggers]
    yield
    for logger, level, propagate, handlers in saved:
        logger.setLevel(level)
        logger.propagate = propagate
        logger.handlers = handlers


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
        mocker.patch.object(posthog_tracker, "Posthog")
        terminal = RecordingHandler()
        logging.getLogger().addHandler(terminal)

        try:
            PostHogTracker(project_api_key="phc_test")
            logging.getLogger("posthog").error("could not deliver the batch")
            logging.getLogger("backoff").info("backing off send_request")
        finally:
            logging.getLogger().removeHandler(terminal)

        assert terminal.records == []

    def test_init__leaves_a_handler_the_caller_attached_working(
        self, mocker: MockerFixture
    ) -> None:
        """Silencing must not destroy the records for an app that wired these loggers up itself."""
        mocker.patch.object(install_id, "get_install_id", return_value=INSTALL_ID)
        mocker.patch.object(posthog_tracker, "Posthog")
        own = RecordingHandler()
        logging.getLogger("backoff").addHandler(own)

        PostHogTracker(project_api_key="phc_test")
        logging.getLogger("backoff").error("giving up on send_request")

        assert len(own.records) == 1

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
