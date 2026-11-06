"""The deployment mode: a local run or an enterprise server.

Use `is_enterprise()` to decide on enterprise behavior. Do not derive it from the database
backend: the Python SDK also uses PostgreSQL after `ls.connect()` to an enterprise instance.
"""

from __future__ import annotations

from enum import Enum

from lightly_studio.database.db_manager import DatabaseBackend
from lightly_studio.dataset import env


class DeploymentMode(str, Enum):
    """How LightlyStudio is deployed.

    LOCAL: A local run, for example after `pip install lightly-studio`. Uses DuckDB.
    ENTERPRISE: A self-hosted server behind the auth proxy. Uses PostgreSQL.
    """

    LOCAL = "local"
    ENTERPRISE = "enterprise"


def get_deployment_mode() -> DeploymentMode:
    """Returns the deployment mode from `LIGHTLY_STUDIO_DEPLOYMENT_MODE`.

    Raises:
        ValueError: If the value is not a known deployment mode.
    """
    value = env.LIGHTLY_STUDIO_DEPLOYMENT_MODE.strip().lower()
    try:
        return DeploymentMode(value)
    except ValueError as error:
        raise ValueError(
            f"Unknown LIGHTLY_STUDIO_DEPLOYMENT_MODE '{env.LIGHTLY_STUDIO_DEPLOYMENT_MODE}'. "
            f"Use one of: {', '.join(mode.value for mode in DeploymentMode)}."
        ) from error


def is_enterprise() -> bool:
    """Returns True if this installation is an enterprise server."""
    return get_deployment_mode() == DeploymentMode.ENTERPRISE


def validate_server_backend(backend: DatabaseBackend) -> None:
    """Raises unless the database backend of the GUI server matches the deployment mode.

    A local run uses DuckDB and an enterprise server uses PostgreSQL. Thus an enterprise
    server without `LIGHTLY_STUDIO_DEPLOYMENT_MODE=enterprise` does not start, instead of
    starting without the enterprise protections.

    Args:
        backend: The database backend of the GUI server.

    Raises:
        ValueError: If the deployment mode is unknown.
        RuntimeError: If the backend does not match the deployment mode.
    """
    mode = get_deployment_mode()
    if mode == DeploymentMode.LOCAL and backend != DatabaseBackend.DUCKDB:
        raise RuntimeError(
            f"The GUI server uses a {backend.value} database, but the GUI supports only DuckDB."
        )
    if mode == DeploymentMode.ENTERPRISE and backend != DatabaseBackend.POSTGRESQL:
        raise RuntimeError(
            f"LIGHTLY_STUDIO_DEPLOYMENT_MODE is 'enterprise', but the GUI server uses a "
            f"{backend.value} database. An enterprise server requires PostgreSQL, set "
            "LIGHTLY_STUDIO_DATABASE_URL."
        )


# Fail at import on an unknown mode, not at the first use
get_deployment_mode()
