from __future__ import annotations

import importlib.util

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK


def test_get_assisted_labeling_status(
    test_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAL_KEY", "secret")

    response = test_client.get("/api/annotate/status")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"unavailable_reason": None}


def test_get_assisted_labeling_status__without_key(
    test_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("FAL_KEY", raising=False)

    response = test_client.get("/api/annotate/status")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"unavailable_reason": "Set the FAL_KEY environment variable."}


def test_get_assisted_labeling_status__without_extra(
    test_client: TestClient, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAL_KEY", "secret")
    mocker.patch.object(importlib.util, "find_spec", return_value=None)

    response = test_client.get("/api/annotate/status")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {
        "unavailable_reason": 'Install the fal extra: pip install "lightly-studio[fal]".'
    }
