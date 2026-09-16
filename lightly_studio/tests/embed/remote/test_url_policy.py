from __future__ import annotations

import re
import socket
import warnings

import httpx
import pytest
from pytest_mock import MockerFixture

from lightly_studio.dataset import env
from lightly_studio.embed.remote import url_policy

API_KEY = "a-token"

# What `socket.getaddrinfo` answers, cut down to the parts the policy reads.
PUBLIC_ADDRESS = "93.184.216.34"
PRIVATE_ADDRESS = "10.0.0.5"


def _allow_private(mocker: MockerFixture, allow: bool) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_REMOTE_EMBEDDER_ALLOW_PRIVATE_URLS", allow)


def _resolve_to(mocker: MockerFixture, addresses: list[str]) -> None:
    infos = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 0)) for address in addresses]
    mocker.patch.object(socket, "getaddrinfo", return_value=infos)


def _assert_no_warning(url: str, api_key: str | None) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        url_policy.check_url(url=url, api_key=api_key)


class TestCheckUrlPermissive:
    """The default mode: any address is usable, a clear-text one only warns."""

    def test_loopback(self, mocker: MockerFixture) -> None:
        _allow_private(mocker=mocker, allow=True)

        _assert_no_warning(url="http://127.0.0.1:8080", api_key=None)

    def test_loopback_name(self, mocker: MockerFixture) -> None:
        _allow_private(mocker=mocker, allow=True)

        _assert_no_warning(url="http://localhost:8080", api_key=None)

    def test_private_address(self, mocker: MockerFixture) -> None:
        _allow_private(mocker=mocker, allow=True)

        with pytest.warns(UserWarning, match="No api_key is set"):
            url_policy.check_url(url="http://10.0.0.5:8080", api_key=None)

    def test_private_address__api_key_in_clear_text(self, mocker: MockerFixture) -> None:
        _allow_private(mocker=mocker, allow=True)

        with pytest.warns(UserWarning, match="bearer token goes with every request"):
            url_policy.check_url(url="http://10.0.0.5:8080", api_key=API_KEY)

    def test_https(self, mocker: MockerFixture) -> None:
        _allow_private(mocker=mocker, allow=True)

        _assert_no_warning(url="https://models.example.com", api_key=None)


class TestCheckUrlStrict:
    """The hosted mode: the address must be TLS and must leave this network."""

    def test_public_address(self, mocker: MockerFixture) -> None:
        _allow_private(mocker=mocker, allow=False)

        url_policy.check_url(url=f"https://{PUBLIC_ADDRESS}", api_key=API_KEY)

    def test_plain_http(self, mocker: MockerFixture) -> None:
        _allow_private(mocker=mocker, allow=False)

        with pytest.raises(ValueError, match="is not https"):
            url_policy.check_url(url="http://models.example.com", api_key=API_KEY)

    def test_loopback(self, mocker: MockerFixture) -> None:
        _allow_private(mocker=mocker, allow=False)

        with pytest.raises(ValueError, match="not a public address"):
            url_policy.check_url(url="https://127.0.0.1", api_key=API_KEY)

    @pytest.mark.parametrize("host", ["10.0.0.5", "192.168.1.10", "172.16.0.1"])
    def test_private_address(self, host: str, mocker: MockerFixture) -> None:
        _allow_private(mocker=mocker, allow=False)

        with pytest.raises(ValueError, match="not a public address"):
            url_policy.check_url(url=f"https://{host}", api_key=API_KEY)

    def test_link_local_address(self, mocker: MockerFixture) -> None:
        # The metadata endpoint of the cloud. It is the reason this control exists.
        _allow_private(mocker=mocker, allow=False)

        with pytest.raises(ValueError, match=re.escape("169.254.169.254")):
            url_policy.check_url(url="https://169.254.169.254", api_key=API_KEY)

    def test_name_resolving_to_a_public_address(self, mocker: MockerFixture) -> None:
        _allow_private(mocker=mocker, allow=False)
        _resolve_to(mocker=mocker, addresses=[PUBLIC_ADDRESS])

        url_policy.check_url(url="https://models.example.com", api_key=API_KEY)

    def test_name_resolving_to_a_private_address(self, mocker: MockerFixture) -> None:
        _allow_private(mocker=mocker, allow=False)
        _resolve_to(mocker=mocker, addresses=[PRIVATE_ADDRESS])

        with pytest.raises(ValueError, match="not a public address"):
            url_policy.check_url(url="https://models.example.com", api_key=API_KEY)

    def test_name_resolving_to_mixed_addresses(self, mocker: MockerFixture) -> None:
        # One name can carry several records. Every one of them must pass.
        _allow_private(mocker=mocker, allow=False)
        _resolve_to(mocker=mocker, addresses=[PUBLIC_ADDRESS, PRIVATE_ADDRESS])

        with pytest.raises(ValueError, match="not a public address"):
            url_policy.check_url(url="https://models.example.com", api_key=API_KEY)

    def test_name_that_does_not_resolve(self, mocker: MockerFixture) -> None:
        _allow_private(mocker=mocker, allow=False)
        mocker.patch.object(socket, "getaddrinfo", side_effect=socket.gaierror("no answer"))

        with pytest.raises(ValueError, match="does not resolve"):
            url_policy.check_url(url="https://models.example.com", api_key=API_KEY)


@pytest.mark.parametrize("allow_private", [True, False])
@pytest.mark.parametrize("url", ["", "models.example.com:8080", "https://", "/v1/describe"])
def test_check_url__not_an_address(url: str, allow_private: bool, mocker: MockerFixture) -> None:
    _allow_private(mocker=mocker, allow=allow_private)

    with pytest.raises(ValueError, match="is not a usable address"):
        url_policy.check_url(url=url, api_key=API_KEY)


def test_check_no_redirects() -> None:
    url_policy.check_no_redirects(client=httpx.Client())


def test_check_no_redirects__following() -> None:
    with pytest.raises(ValueError, match="must not follow redirects"):
        url_policy.check_no_redirects(client=httpx.Client(follow_redirects=True))
