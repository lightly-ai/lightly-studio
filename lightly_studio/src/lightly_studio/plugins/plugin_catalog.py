"""Catalog of the plugins that can be installed from the LightlyStudio plugins repository."""

from __future__ import annotations

import importlib.metadata
import logging
import re
import sys
import threading
import time
from typing import Any

import httpx
from pydantic import BaseModel

from lightly_studio.dataset import env
from lightly_studio.errors import NotFoundError

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

logger = logging.getLogger(__name__)

PLUGINS_REPOSITORY_URL = "https://github.com/lightly-ai/lightly-studio-plugins.git"
CATALOG_CACHE_SECONDS = 600.0
_FETCH_TIMEOUT_SECONDS = 10.0
_LOCAL_SOURCE_PREFIX = "local:"


class CatalogEntry(BaseModel):
    """A plugin in the catalog."""

    id: str
    """The distribution name of the plugin, for example ``lightly_plugins_sam3_segmentation``."""

    name: str
    description: str = ""
    maintainer: str = ""

    install_spec: str
    """The requirement that is given to the installer, for example a ``git+https`` URL."""


class CatalogUnavailableError(Exception):
    """Exception raised when the plugin catalog cannot be fetched or parsed."""


class _CatalogCache:
    """Keeps the last fetched catalog for ``CATALOG_CACHE_SECONDS``."""

    def __init__(self) -> None:
        self.entries: list[CatalogEntry] | None = None
        self.fetched_at = 0.0
        self.lock = threading.Lock()


_cache = _CatalogCache()


def get_catalog(force_refresh: bool = False) -> list[CatalogEntry]:
    """Get the plugin catalog. The result is cached for ``CATALOG_CACHE_SECONDS``.

    Args:
        force_refresh: Fetch the catalog also if the cached copy is not expired.

    Returns:
        The catalog entries.

    Raises:
        CatalogUnavailableError: If the catalog cannot be fetched or parsed.
    """
    with _cache.lock:
        is_expired = time.monotonic() - _cache.fetched_at > CATALOG_CACHE_SECONDS
        if _cache.entries is None or is_expired or force_refresh:
            _cache.entries = parse_catalog(
                text=_fetch_catalog_text(url=env.LIGHTLY_STUDIO_PLUGIN_CATALOG_URL)
            )
            _cache.fetched_at = time.monotonic()
        return _cache.entries


def get_entry(plugin_id: str) -> CatalogEntry:
    """Get one catalog entry by its ID.

    Raises:
        NotFoundError: If the catalog has no plugin with this ID.
        CatalogUnavailableError: If the catalog cannot be fetched or parsed.
    """
    for entry in get_catalog():
        if entry.id == plugin_id:
            return entry
    raise NotFoundError(f"Plugin '{plugin_id}' is not in the plugin catalog.")


def is_installed(package_name: str) -> bool:
    """Return whether a distribution with this name is installed in the current environment."""
    try:
        importlib.metadata.distribution(package_name)
    except importlib.metadata.PackageNotFoundError:
        return False
    return True


def normalize_package_name(name: str) -> str:
    """Normalize a distribution name as specified in PEP 503."""
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_catalog(text: str) -> list[CatalogEntry]:
    """Parse the ``plugins.toml`` file of the plugins repository.

    Entries with a source that cannot be installed are skipped.

    Args:
        text: The content of ``plugins.toml``.

    Returns:
        The catalog entries.

    Raises:
        CatalogUnavailableError: If the text is not valid TOML.
    """
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        raise CatalogUnavailableError(f"The plugin catalog is not valid TOML: {e}") from e

    entries = []
    for raw in data.get("plugins", []):
        entry = _parse_entry(raw=raw)
        if entry is not None:
            entries.append(entry)
    return entries


def _fetch_catalog_text(url: str) -> str:
    try:
        response = httpx.get(url, timeout=_FETCH_TIMEOUT_SECONDS, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as e:
        raise CatalogUnavailableError(f"Cannot fetch the plugin catalog from {url}: {e}") from e
    return response.text


def _parse_entry(raw: dict[str, Any]) -> CatalogEntry | None:
    plugin_id = raw.get("id")
    source = raw.get("source")
    if not isinstance(plugin_id, str) or not isinstance(source, str):
        logger.warning("Skipping a plugin catalog entry without 'id' or 'source': %s", raw)
        return None
    install_spec = _install_spec(source=source)
    if install_spec is None:
        logger.info("Skipping plugin '%s' with unsupported source '%s'.", plugin_id, source)
        return None
    return CatalogEntry(
        id=plugin_id,
        name=raw.get("name", plugin_id),
        description=raw.get("description", ""),
        maintainer=raw.get("maintainer", ""),
        install_spec=install_spec,
    )


def _install_spec(source: str) -> str | None:
    """Map the ``source`` of a catalog entry to a requirement for the installer.

    A ``local:<path>`` source is a directory in the plugins repository. Other sources are not
    supported yet.
    """
    if not source.startswith(_LOCAL_SOURCE_PREFIX):
        return None
    subdirectory = source[len(_LOCAL_SOURCE_PREFIX) :].strip("/")
    # The subdirectory goes into a URL fragment. Reject anything that could change the URL.
    if (
        not subdirectory
        or not re.fullmatch(r"[A-Za-z0-9_./-]+", subdirectory)
        or ".." in subdirectory
    ):
        return None
    return f"git+{PLUGINS_REPOSITORY_URL}#subdirectory={subdirectory}"
