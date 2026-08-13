import atexit
import threading
import time
from collections.abc import Generator, Mapping

import pytest
from pytest_mock import MockerFixture

from lightly_studio.analytics import tracking


class FakeTracker:
    """Records what it was asked to send."""

    def __init__(self) -> None:
        self.events: list[tuple[str, Mapping[str, object]]] = []
        self.shutdown_calls = 0

    def track(self, event: str, properties: Mapping[str, object]) -> None:
        self.events.append((event, properties))

    def shutdown(self) -> None:
        self.shutdown_calls += 1


class BrokenTracker:
    """Stands in for a backend that is down or misconfigured."""

    def track(self, event: str, properties: Mapping[str, object]) -> None:
        raise RuntimeError(f"unreachable, dropped '{event}' with {properties}")

    def shutdown(self) -> None:
        raise RuntimeError("unreachable, could not flush")


@pytest.fixture(autouse=True)
def reset_tracker() -> Generator[None, None, None]:
    """Clear the process-wide tracker so tests do not leak into each other."""
    tracking._tracker = None
    yield
    tracking._tracker = None


def test_track(mocker: MockerFixture) -> None:
    fake = FakeTracker()
    mocker.patch.object(tracking, "_create_tracker", return_value=fake)

    tracking.track(
        event=tracking.APP_LAUNCHED,
        properties={"launch_source": tracking.LaunchSource.QUICKSTART.value},
    )

    assert fake.events == [(tracking.APP_LAUNCHED, {"launch_source": "quickstart"})]


def test_track__builds_the_tracker_once(mocker: MockerFixture) -> None:
    fake = FakeTracker()
    create = mocker.patch.object(tracking, "_create_tracker", return_value=fake)

    tracking.track(event=tracking.APP_LAUNCHED, properties={})
    tracking.track(event=tracking.APP_LAUNCHED, properties={})

    create.assert_called_once_with()
    assert len(fake.events) == 2


def test_track__builds_the_tracker_once_under_concurrency(mocker: MockerFixture) -> None:
    """Concurrent callers must share one tracker, or an event is queued on an orphan."""

    def build_tracker() -> FakeTracker:
        # Sleeping releases the GIL, so every thread reaches the None check before the first
        # construction finishes. Without a lock they all build their own tracker.
        time.sleep(0.01)
        return FakeTracker()

    create = mocker.patch.object(tracking, "_create_tracker", side_effect=build_tracker)
    threads = [
        threading.Thread(
            target=tracking.track,
            kwargs={"event": tracking.APP_LAUNCHED, "properties": {}},
        )
        for _ in range(8)
    ]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    create.assert_called_once_with()


def test_track__when_the_backend_raises(mocker: MockerFixture) -> None:
    """A broken analytics backend must never surface to the caller."""
    mocker.patch.object(tracking, "_create_tracker", return_value=BrokenTracker())

    tracking.track(event=tracking.APP_LAUNCHED, properties={})


def test_shutdown(mocker: MockerFixture) -> None:
    fake = FakeTracker()
    mocker.patch.object(tracking, "_create_tracker", return_value=fake)
    tracking.track(event=tracking.APP_LAUNCHED, properties={})

    tracking.shutdown()

    assert fake.shutdown_calls == 1


def test_shutdown__without_a_tracker() -> None:
    tracking.shutdown()


def test_shutdown__when_the_backend_raises(mocker: MockerFixture) -> None:
    mocker.patch.object(tracking, "_create_tracker", return_value=BrokenTracker())
    tracking.track(event=tracking.APP_LAUNCHED, properties={})

    tracking.shutdown()


def test_create_tracker(mocker: MockerFixture) -> None:
    mocker.patch.object(tracking, "LIGHTLY_STUDIO_ANALYTICS_ENABLED", True)
    mocker.patch.object(tracking, "LIGHTLY_STUDIO_POSTHOG_KEY", "phc_test")
    mocker.patch.object(atexit, "register")
    posthog_tracker = mocker.patch.object(tracking, "PostHogTracker")

    tracker = tracking._create_tracker()

    posthog_tracker.assert_called_once_with(project_api_key="phc_test")
    assert tracker is posthog_tracker.return_value


def test_create_tracker__flushes_at_exit(mocker: MockerFixture) -> None:
    """Without this hook a short-lived process drops the queued event."""
    mocker.patch.object(tracking, "LIGHTLY_STUDIO_ANALYTICS_ENABLED", True)
    mocker.patch.object(tracking, "LIGHTLY_STUDIO_POSTHOG_KEY", "phc_test")
    mocker.patch.object(tracking, "PostHogTracker")
    register = mocker.patch.object(atexit, "register")

    tracking._create_tracker()

    register.assert_called_once_with(tracking.shutdown)


def test_create_tracker__when_analytics_are_disabled(mocker: MockerFixture) -> None:
    mocker.patch.object(tracking, "LIGHTLY_STUDIO_ANALYTICS_ENABLED", False)
    mocker.patch.object(tracking, "LIGHTLY_STUDIO_POSTHOG_KEY", "phc_test")

    assert isinstance(tracking._create_tracker(), tracking.NoOpTracker)


def test_create_tracker__without_a_key(mocker: MockerFixture) -> None:
    mocker.patch.object(tracking, "LIGHTLY_STUDIO_ANALYTICS_ENABLED", True)
    mocker.patch.object(tracking, "LIGHTLY_STUDIO_POSTHOG_KEY", "")

    assert isinstance(tracking._create_tracker(), tracking.NoOpTracker)
