from __future__ import annotations

import httpx
import pytest
from pytest_mock import MockerFixture

from lightly_studio.dataset import env
from lightly_studio.errors import NotFoundError
from lightly_studio.plugins import plugin_catalog
from lightly_studio.plugins.plugin_catalog import CatalogEntry, CatalogUnavailableError

_CATALOG_TOML = """
[[plugins]]
id = "lightly_plugins_sam3_segmentation"
name = "SAM3"
description = "Segments all instances"
source = "local:plugins/sam3_segmentation"
maintainer = "lightly"
tags = ["auto-labeling", "segmentation"]

[[plugins]]
id = "third_party_plugin"
name = "Third party"
source = "pypi:third_party_plugin"
"""

_SAM3_ENTRY = CatalogEntry(
    id="lightly_plugins_sam3_segmentation",
    name="SAM3",
    description="Segments all instances",
    maintainer="lightly",
    install_spec=(
        "git+https://github.com/lightly-ai/lightly-studio-plugins.git"
        "#subdirectory=plugins/sam3_segmentation"
    ),
)


@pytest.fixture(autouse=True)
def _empty_cache(mocker: MockerFixture) -> None:
    mocker.patch.object(plugin_catalog, "_cache", plugin_catalog._CatalogCache())


def test_get_catalog(mocker: MockerFixture) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_PLUGIN_CATALOG_URL", "https://example.com/p.toml")
    get = mocker.patch.object(
        httpx, "get", return_value=httpx.Response(200, text=_CATALOG_TOML, request=_request())
    )

    assert plugin_catalog.get_catalog() == [_SAM3_ENTRY]
    get.assert_called_once()
    assert get.call_args.args == ("https://example.com/p.toml",)


def test_get_catalog__cached(mocker: MockerFixture) -> None:
    get = mocker.patch.object(
        httpx, "get", return_value=httpx.Response(200, text=_CATALOG_TOML, request=_request())
    )

    plugin_catalog.get_catalog()
    plugin_catalog.get_catalog()

    get.assert_called_once()


def test_get_catalog__force_refresh(mocker: MockerFixture) -> None:
    get = mocker.patch.object(
        httpx, "get", return_value=httpx.Response(200, text=_CATALOG_TOML, request=_request())
    )

    plugin_catalog.get_catalog()
    plugin_catalog.get_catalog(force_refresh=True)

    assert get.call_count == 2


def test_get_catalog__http_error(mocker: MockerFixture) -> None:
    mocker.patch.object(
        httpx, "get", return_value=httpx.Response(404, text="Not Found", request=_request())
    )

    with pytest.raises(CatalogUnavailableError, match="Cannot fetch the plugin catalog"):
        plugin_catalog.get_catalog()


def test_get_catalog__network_error(mocker: MockerFixture) -> None:
    mocker.patch.object(httpx, "get", side_effect=httpx.ConnectError("offline"))

    with pytest.raises(CatalogUnavailableError, match="offline"):
        plugin_catalog.get_catalog()


def test_get_entry(mocker: MockerFixture) -> None:
    mocker.patch.object(plugin_catalog, "get_catalog", return_value=[_SAM3_ENTRY])

    assert plugin_catalog.get_entry(plugin_id="lightly_plugins_sam3_segmentation") == _SAM3_ENTRY
    with pytest.raises(NotFoundError, match="'unknown' is not in the plugin catalog"):
        plugin_catalog.get_entry(plugin_id="unknown")


def test_is_installed() -> None:
    assert plugin_catalog.is_installed(package_name="lightly-studio")
    assert not plugin_catalog.is_installed(package_name="lightly_plugins_does_not_exist")


def test_normalize_package_name() -> None:
    assert plugin_catalog.normalize_package_name("Lightly_Plugins.SAM3") == "lightly-plugins-sam3"


def test_parse_catalog() -> None:
    assert plugin_catalog.parse_catalog(text=_CATALOG_TOML) == [_SAM3_ENTRY]


def test_parse_catalog__invalid_toml() -> None:
    with pytest.raises(CatalogUnavailableError, match="not valid TOML"):
        plugin_catalog.parse_catalog(text="[[plugins]\n")


def test_parse_catalog__missing_fields() -> None:
    assert plugin_catalog.parse_catalog(text='[[plugins]]\nname = "No id"\n') == []


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "local:plugins/yolo",
            "git+https://github.com/lightly-ai/lightly-studio-plugins.git#subdirectory=plugins/yolo",
        ),
        ("local:", None),
        ("local:plugins/../../evil", None),
        ("local:plugins/a&b", None),
        ("pypi:yolo", None),
    ],
)
def test_install_spec(source: str, expected: str | None) -> None:
    assert plugin_catalog._install_spec(source=source) == expected


def _request() -> httpx.Request:
    return httpx.Request("GET", "https://example.com/plugins.toml")
