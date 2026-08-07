from __future__ import annotations

import pytest

from lightly_studio.dataset import embedding_service


def test_validate_serving_url() -> None:
    assert embedding_service.validate_serving_url("https://embeddings.corp.example") == (
        "https://embeddings.corp.example"
    )


def test_validate_serving_url__strips_trailing_slash() -> None:
    assert embedding_service.validate_serving_url("https://embeddings.corp.example/") == (
        "https://embeddings.corp.example"
    )


@pytest.mark.parametrize(
    "serving_url",
    [
        "http://localhost:8123",
        "http://127.0.0.1:8123",
        "http://[::1]:8123",
    ],
)
def test_validate_serving_url__plain_http_on_loopback(serving_url: str) -> None:
    """Loopback is exempt: the browser treats it as a secure context."""
    assert embedding_service.validate_serving_url(serving_url) == serving_url


def test_validate_serving_url__plain_http_on_lan_host() -> None:
    """A hosted Studio page is served over HTTPS, so plain http is blocked as mixed content."""
    with pytest.raises(ValueError, match="must use https"):
        embedding_service.validate_serving_url("http://192.168.1.20:8123")


def test_validate_serving_url__unsupported_scheme() -> None:
    with pytest.raises(ValueError, match="must use https"):
        embedding_service.validate_serving_url("ftp://embeddings.corp.example")


def test_validate_serving_url__missing_host() -> None:
    with pytest.raises(ValueError, match="host"):
        embedding_service.validate_serving_url("https://")
