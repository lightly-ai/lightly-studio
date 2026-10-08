from __future__ import annotations

from fastapi.testclient import TestClient

from lightly_studio.api.routes.api.status import HTTP_STATUS_BAD_REQUEST, HTTP_STATUS_OK


def test_set_settings__assisted_labeling_provider(test_client: TestClient) -> None:
    settings = test_client.get("/api/settings").json()

    response = test_client.post(
        "/api/settings", json={**settings, "assisted_labeling_provider": "fake"}
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json()["assisted_labeling_provider"] == "fake"


def test_set_settings__unknown_assisted_labeling_provider(test_client: TestClient) -> None:
    settings = test_client.get("/api/settings").json()

    response = test_client.post(
        "/api/settings", json={**settings, "assisted_labeling_provider": "unknown"}
    )

    assert response.status_code == HTTP_STATUS_BAD_REQUEST
    assert "Unknown assisted labeling provider 'unknown'" in response.json()["error"]
    assert test_client.get("/api/settings").json()["assisted_labeling_provider"] == "fal_sam3"
