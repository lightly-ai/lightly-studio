from __future__ import annotations

import json

import httpx
import pytest

from lightly_studio.transport.remote import http_requests


def test_get() -> None:
    sent: list[httpx.Request] = []
    client = _client(status_code=200, body=["root"], sent=sent)
    params = {"name": "root", "parent_collection_id": None}

    body = http_requests.get(client=client, path="/collections", params=params)

    assert body == ["root"]
    assert str(sent[0].url) == "http://studio/api/v1/collections?name=root"


def test_get__not_found__returns_none() -> None:
    client = _client(status_code=404, body={"error": "Collection not found."})

    assert http_requests.get(client=client, path="/x") is None


@pytest.mark.parametrize("body", [{"detail": "Not Found"}, None, "error", b"Not Found"])
def test_get__unknown_route__raises(body: object) -> None:
    client = _client(status_code=404, body=body)

    with pytest.raises(httpx.HTTPStatusError):
        http_requests.get(client=client, path="/x")


def test_post() -> None:
    sent: list[httpx.Request] = []
    client = _client(status_code=200, body={"tag_id": "1"}, sent=sent)

    body = http_requests.post(client=client, path="/tags", body={"name": "cat"})

    assert body == {"tag_id": "1"}
    assert sent[0].url.path == "/api/v1/tags"
    assert json.loads(sent[0].content) == {"name": "cat"}


def test_post__no_content__returns_none() -> None:
    client = _client(status_code=204, body=None)

    assert http_requests.post(client=client, path="/tags", body={}) is None


@pytest.mark.parametrize(
    ("status_code", "body", "message"),
    [
        (400, {"error": "bad cursor"}, "bad cursor"),
        (400, b"bad cursor", "bad cursor"),
        (422, {"detail": ["too long"]}, "too long"),
    ],
)
def test_post__rejected__raises(status_code: int, body: object, message: str) -> None:
    client = _client(status_code=status_code, body=body)

    with pytest.raises(ValueError, match=message):
        http_requests.post(client=client, path="/x", body={})


def test_post__server_error__raises() -> None:
    with pytest.raises(httpx.HTTPStatusError):
        http_requests.post(client=_client(status_code=500, body={}), path="/x", body={})


def _client(
    status_code: int, body: object, sent: list[httpx.Request] | None = None
) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if sent is not None:
            sent.append(request)
        content = body if isinstance(body, bytes) else json.dumps(body)
        return httpx.Response(status_code=status_code, content=content)

    return httpx.Client(transport=httpx.MockTransport(handler), base_url="http://studio")
