from __future__ import annotations

import pytest
from pytest_mock import MockerFixture

from lightly_studio import deployment
from lightly_studio.database.db_manager import DatabaseBackend
from lightly_studio.dataset import env
from lightly_studio.deployment import DeploymentMode


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("local", DeploymentMode.LOCAL),
        ("enterprise", DeploymentMode.ENTERPRISE),
        (" Enterprise ", DeploymentMode.ENTERPRISE),
    ],
)
def test_get_deployment_mode(mocker: MockerFixture, value: str, expected: DeploymentMode) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_DEPLOYMENT_MODE", value)
    assert deployment.get_deployment_mode() == expected


def test_get_deployment_mode__unknown(mocker: MockerFixture) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_DEPLOYMENT_MODE", "hosted")
    with pytest.raises(ValueError, match="Unknown LIGHTLY_STUDIO_DEPLOYMENT_MODE 'hosted'"):
        deployment.get_deployment_mode()


@pytest.mark.parametrize(("value", "expected"), [("local", False), ("enterprise", True)])
def test_is_enterprise(mocker: MockerFixture, value: str, expected: bool) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_DEPLOYMENT_MODE", value)
    assert deployment.is_enterprise() is expected


@pytest.mark.parametrize(
    ("value", "backend"),
    [
        ("local", DatabaseBackend.DUCKDB),
        ("enterprise", DatabaseBackend.POSTGRESQL),
    ],
)
def test_validate_server_backend(
    mocker: MockerFixture, value: str, backend: DatabaseBackend
) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_DEPLOYMENT_MODE", value)
    deployment.validate_server_backend(backend=backend)


def test_validate_server_backend__local_with_postgres(mocker: MockerFixture) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_DEPLOYMENT_MODE", "local")
    with pytest.raises(RuntimeError, match="the GUI supports only DuckDB"):
        deployment.validate_server_backend(backend=DatabaseBackend.POSTGRESQL)


def test_validate_server_backend__enterprise_with_duckdb(mocker: MockerFixture) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_DEPLOYMENT_MODE", "enterprise")
    with pytest.raises(RuntimeError, match="An enterprise server requires PostgreSQL"):
        deployment.validate_server_backend(backend=DatabaseBackend.DUCKDB)
