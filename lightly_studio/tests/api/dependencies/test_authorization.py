from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from lightly_studio.api.dependencies import authorization
from lightly_studio.api.dependencies.authorization import Action, AllowAll
from lightly_studio.api.dependencies.identity import Identity
from lightly_studio.api.routes.api import exceptions
from lightly_studio.api.routes.api.status import HTTP_STATUS_FORBIDDEN, HTTP_STATUS_OK


class _DenyAll:
    def allows(self, identity: Identity, action: Action) -> bool:  # noqa: ARG002
        return False


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()
    exceptions.register_exception_handlers(app=app)

    @app.delete(
        "/dataset",
        dependencies=[Depends(authorization.require(Action.DATASET_DELETE))],
    )
    def _delete_dataset() -> dict[str, str]:
        return {"status": "deleted"}

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def test_get_policy() -> None:
    assert isinstance(authorization.get_policy(), AllowAll)


def test_require(client: TestClient) -> None:
    response = client.delete("/dataset")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"status": "deleted"}


def test_require__override_denies(app: FastAPI, client: TestClient) -> None:
    app.dependency_overrides[authorization.get_policy] = _DenyAll

    response = client.delete("/dataset")

    assert response.status_code == HTTP_STATUS_FORBIDDEN
    assert response.json() == {"error": "The action 'dataset.delete' is not allowed."}
