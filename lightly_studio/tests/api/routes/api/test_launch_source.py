from collections.abc import Generator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from lightly_studio.api import launch_source
from lightly_studio.api.launch_source import LaunchSource


@pytest.fixture(autouse=True)
def reset_launch_source() -> Generator[None, None, None]:
    """Reset the process-global launch source so tests do not leak into each other."""
    launch_source.set_launch_source(source=LaunchSource.SDK)
    yield
    launch_source.set_launch_source(source=LaunchSource.SDK)


def test_get_launch_source(test_client: TestClient) -> None:
    response = test_client.get("/api/launch-source")
    assert response.status_code == 200
    assert response.json()["launch_source"] == "sdk"


def test_get_launch_source__quickstart(test_client: TestClient) -> None:
    launch_source.set_launch_source(source=LaunchSource.QUICKSTART)
    response = test_client.get("/api/launch-source")
    assert response.status_code == 200
    assert response.json()["launch_source"] == "quickstart"


def test_get_launch_source__gui(test_client: TestClient) -> None:
    launch_source.set_launch_source(source=LaunchSource.GUI)
    response = test_client.get("/api/launch-source")
    assert response.status_code == 200
    assert response.json()["launch_source"] == "gui"


def test_get_launch_source__launch_id_is_a_uuid(test_client: TestClient) -> None:
    response = test_client.get("/api/launch-source")
    assert response.status_code == 200
    assert UUID(response.json()["launch_id"]) == launch_source.get_launch_id()


def test_get_launch_source__launch_id_is_stable_within_a_process(test_client: TestClient) -> None:
    """The GUI reports a launch once by comparing this ID, so it must not change between calls."""
    first = test_client.get("/api/launch-source").json()["launch_id"]
    launch_source.set_launch_source(source=LaunchSource.QUICKSTART)
    second = test_client.get("/api/launch-source").json()["launch_id"]
    assert first == second
