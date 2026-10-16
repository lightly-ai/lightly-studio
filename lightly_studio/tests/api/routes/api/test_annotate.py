from __future__ import annotations

from fastapi.testclient import TestClient

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from lightly_studio.assisted_labeling import provider_ids
from lightly_studio.assisted_labeling.fake_provider import FakeProvider


def test_list_providers(test_client: TestClient) -> None:
    response = test_client.get("/api/annotate/providers")

    assert response.status_code == HTTP_STATUS_OK
    providers = response.json()
    by_id = {provider["provider_id"]: provider for provider in providers}
    assert provider_ids.FAKE_PROVIDER_ID in by_id
    assert provider_ids.FAL_SAM3_PROVIDER_ID in by_id
    fake = by_id[provider_ids.FAKE_PROVIDER_ID]
    assert fake["capabilities"] == FakeProvider().capabilities().model_dump()
    assert fake["unavailable_reason"] is None
