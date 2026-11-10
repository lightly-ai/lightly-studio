from __future__ import annotations

from fastapi.testclient import TestClient

from lightly_studio.api.app import app
from lightly_studio.api.dependencies import authorization
from lightly_studio.api.dependencies.authorization import Action
from lightly_studio.api.dependencies.identity import Identity
from lightly_studio.api.routes.api.status import HTTP_STATUS_OK


class _DenyAll:
    def allows(self, identity: Identity, action: Action) -> bool:  # noqa: ARG002
        return False


def test_get_capabilities(test_client: TestClient) -> None:
    response = test_client.get("/api/capabilities")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"actions": ["dataset.delete"]}


def test_get_capabilities__override_denies(test_client: TestClient) -> None:
    app.dependency_overrides[authorization.get_policy] = _DenyAll

    response = test_client.get("/api/capabilities")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"actions": []}
