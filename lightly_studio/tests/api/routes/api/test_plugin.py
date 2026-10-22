from __future__ import annotations

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_FORBIDDEN,
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_OK,
    HTTP_STATUS_SERVICE_UNAVAILABLE,
)
from lightly_studio.dataset import env
from lightly_studio.plugins import plugin_catalog, plugin_installer
from lightly_studio.plugins.plugin_catalog import CatalogEntry, CatalogUnavailableError
from lightly_studio.plugins.plugin_installer import InstallJob

_ENTRY = CatalogEntry(
    id="lightly_plugins_demo",
    name="Demo",
    description="A demo plugin",
    maintainer="lightly",
    install_spec="git+https://x#y",
)


def test_get_plugin_catalog(test_client: TestClient, mocker: MockerFixture) -> None:
    mocker.patch.object(plugin_catalog, "get_catalog", return_value=[_ENTRY])
    mocker.patch.object(plugin_catalog, "is_installed", return_value=True)
    mocker.patch.object(env, "LIGHTLY_STUDIO_ALLOW_PLUGIN_INSTALL", None)

    response = test_client.get("/api/plugins/catalog")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {
        "plugins": [
            {
                "id": "lightly_plugins_demo",
                "name": "Demo",
                "description": "A demo plugin",
                "maintainer": "lightly",
                "installed": True,
            }
        ],
        # The test client address is "testclient", which is not a loopback address.
        "install_allowed": False,
    }


def test_get_plugin_catalog__unavailable(test_client: TestClient, mocker: MockerFixture) -> None:
    mocker.patch.object(
        plugin_catalog, "get_catalog", side_effect=CatalogUnavailableError("offline")
    )

    response = test_client.get("/api/plugins/catalog")

    assert response.status_code == HTTP_STATUS_SERVICE_UNAVAILABLE
    assert response.json() == {"error": "offline"}


def test_install_plugin(test_client: TestClient, mocker: MockerFixture) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_ALLOW_PLUGIN_INSTALL", True)
    mocker.patch.object(plugin_catalog, "get_catalog", return_value=[_ENTRY])
    start_install = mocker.patch.object(
        plugin_installer,
        "start_install",
        return_value=InstallJob(job_id="job-1", plugin_id="lightly_plugins_demo"),
    )

    response = test_client.post("/api/plugins/catalog/lightly_plugins_demo/install")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json()["job_id"] == "job-1"
    assert response.json()["status"] == "queued"
    start_install.assert_called_once_with(entry=_ENTRY)


def test_install_plugin__not_allowed(test_client: TestClient, mocker: MockerFixture) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_ALLOW_PLUGIN_INSTALL", False)
    start_install = mocker.patch.object(plugin_installer, "start_install")

    response = test_client.post("/api/plugins/catalog/lightly_plugins_demo/install")

    assert response.status_code == HTTP_STATUS_FORBIDDEN
    start_install.assert_not_called()


def test_install_plugin__unknown_plugin(test_client: TestClient, mocker: MockerFixture) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_ALLOW_PLUGIN_INSTALL", True)
    mocker.patch.object(plugin_catalog, "get_catalog", return_value=[_ENTRY])
    start_install = mocker.patch.object(plugin_installer, "start_install")

    response = test_client.post("/api/plugins/catalog/unknown/install")

    assert response.status_code == HTTP_STATUS_NOT_FOUND
    start_install.assert_not_called()


def test_get_plugin_install_job(test_client: TestClient, mocker: MockerFixture) -> None:
    mocker.patch.object(
        plugin_installer, "_jobs", {"job-1": InstallJob(job_id="job-1", plugin_id="p")}
    )

    response = test_client.get("/api/plugins/install-jobs/job-1")
    assert response.status_code == HTTP_STATUS_OK
    assert response.json()["plugin_id"] == "p"

    response = test_client.get("/api/plugins/install-jobs/job-2")
    assert response.status_code == HTTP_STATUS_NOT_FOUND
