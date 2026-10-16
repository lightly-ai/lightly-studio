from __future__ import annotations

from fastapi.testclient import TestClient

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_REQUEST,
    HTTP_STATUS_OK,
)
from lightly_studio.assisted_labeling import provider_ids


def test_set_settings__known_provider(test_client: TestClient) -> None:
    settings = test_client.get("/api/settings").json()
    settings["assisted_labeling_provider"] = provider_ids.FAKE_PROVIDER_ID

    response = test_client.post("/api/settings", json=settings)

    assert response.status_code == HTTP_STATUS_OK
    assert response.json()["assisted_labeling_provider"] == provider_ids.FAKE_PROVIDER_ID


def test_set_settings__unknown_provider(test_client: TestClient) -> None:
    settings = test_client.get("/api/settings").json()
    settings["assisted_labeling_provider"] = "unknown"

    response = test_client.post("/api/settings", json=settings)

    assert response.status_code == HTTP_STATUS_BAD_REQUEST
    assert response.json() == {"error": "Unknown assisted labeling provider 'unknown'."}
    after = test_client.get("/api/settings").json()
    assert after["assisted_labeling_provider"] == provider_ids.DEFAULT_PROVIDER_ID
