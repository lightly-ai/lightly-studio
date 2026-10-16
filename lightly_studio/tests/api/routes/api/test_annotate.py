from __future__ import annotations

from fastapi.testclient import TestClient

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from lightly_studio.assisted_labeling import provider_ids
from lightly_studio.assisted_labeling.fake_provider import FakeProvider


def test_list_providers(test_client: TestClient) -> None:
    response = test_client.get("/api/annotate/providers")

    assert response.status_code == HTTP_STATUS_OK
    providers = response.json()
    assert len(providers) == 1
    assert providers[0]["provider_id"] == provider_ids.FAKE_PROVIDER_ID
    assert providers[0]["capabilities"] == FakeProvider().capabilities().model_dump()
    assert providers[0]["unavailable_reason"] is None
