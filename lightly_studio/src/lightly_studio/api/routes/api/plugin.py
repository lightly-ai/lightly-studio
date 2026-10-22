"""API routes to browse and install plugins from the plugin catalog."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from lightly_studio.plugins import plugin_catalog, plugin_installer
from lightly_studio.plugins.plugin_installer import InstallJob, PluginInstallNotAllowedError

plugin_router = APIRouter(prefix="/plugins", tags=["plugins"])


class CatalogPluginView(BaseModel):
    """A catalog plugin as exposed to the GUI."""

    id: str
    name: str
    description: str
    maintainer: str
    installed: bool


class PluginCatalogView(BaseModel):
    """The plugin catalog as exposed to the GUI."""

    plugins: list[CatalogPluginView]
    install_allowed: bool
    """Whether the client may install plugins from the GUI."""


@plugin_router.get("/catalog")
def get_plugin_catalog(request: Request, refresh: bool = False) -> PluginCatalogView:
    """Get the plugins that can be installed, and whether each one is installed.

    Args:
        request: The request, to decide whether the client may install plugins.
        refresh: Fetch the catalog again, also if the cached copy is not expired.
    """
    entries = plugin_catalog.get_catalog(force_refresh=refresh)
    return PluginCatalogView(
        plugins=[
            CatalogPluginView(
                id=entry.id,
                name=entry.name,
                description=entry.description,
                maintainer=entry.maintainer,
                installed=plugin_catalog.is_installed(package_name=entry.id),
            )
            for entry in entries
        ],
        install_allowed=plugin_installer.is_install_allowed(client_host=_client_host(request)),
    )


@plugin_router.post("/catalog/{plugin_id}/install")
def install_plugin(plugin_id: str, request: Request) -> InstallJob:
    """Start to install a catalog plugin into the environment of the server.

    The install runs in the background. Poll ``GET /plugins/install-jobs/{job_id}`` for its state.
    """
    if not plugin_installer.is_install_allowed(client_host=_client_host(request)):
        raise PluginInstallNotAllowedError(
            "Plugin installs are only allowed from the machine that runs LightlyStudio. "
            "Set LIGHTLY_STUDIO_ALLOW_PLUGIN_INSTALL=true to allow them from other machines."
        )
    entry = plugin_catalog.get_entry(plugin_id=plugin_id)
    return plugin_installer.start_install(entry=entry)


@plugin_router.get("/install-jobs/{job_id}")
def get_plugin_install_job(job_id: str) -> InstallJob:
    """Get the state of a plugin install job."""
    return plugin_installer.get_job(job_id=job_id)


def _client_host(request: Request) -> str | None:
    return request.client.host if request.client is not None else None
