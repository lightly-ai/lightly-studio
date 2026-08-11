from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from lightly_studio.api import launch_source
from lightly_studio.api.launch_source import LaunchSource


@pytest.fixture(autouse=True)
def reset_launch_source() -> Generator[None, None, None]:
    """Reset the process-global launch source so tests do not leak into each other."""
    yield
    launch_source.set_launch_source(source=LaunchSource.SDK)


def test_get_launch_source(test_client: TestClient) -> None:
    response = test_client.get("/api/launch-source")
    assert response.status_code == 200
    assert response.json() == {"launch_source": "sdk"}


def test_get_launch_source__quickstart(test_client: TestClient) -> None:
    launch_source.set_launch_source(source=LaunchSource.QUICKSTART)
    response = test_client.get("/api/launch-source")
    assert response.status_code == 200
    assert response.json() == {"launch_source": "quickstart"}


def test_get_launch_source__gui(test_client: TestClient) -> None:
    launch_source.set_launch_source(source=LaunchSource.GUI)
    response = test_client.get("/api/launch-source")
    assert response.status_code == 200
    assert response.json() == {"launch_source": "gui"}
