from __future__ import annotations

import pytest

from lightly_studio_serve.conformance import __main__ as main_module
from lightly_studio_serve.server import create_app
from tests.conformance import helpers
from tests.conformance.helpers import FakeEmbedder

API_KEY = "the-key"


def test_main(capsys: pytest.CaptureFixture[str]) -> None:
    """The server of this package passes over a real socket, which is what CI runs."""
    with helpers.serving(app=create_app(embedder=FakeEmbedder())) as url:
        status = main_module.main(argv=[url])

    output = capsys.readouterr().out
    assert status == 0
    assert _rows(output=output) >= {"text passed", "image_bytes passed", "video_bytes passed"}
    assert output.endswith("PASSED\n")


def test_main__server_that_breaks_the_protocol(capsys: pytest.CaptureFixture[str]) -> None:
    app = helpers.canned_app(
        describe=helpers.describe_body(),
        embeddings=helpers.embeddings_body(dimension=3, embeddings=[[1.0, 1.0, 1.0]]),
    )
    with helpers.serving(app=app) as url:
        status = main_module.main(argv=[url])

    output = capsys.readouterr().out
    assert status == 1
    assert "text failed" in _rows(output=output)
    assert "answers dimension 3, /v1/describe answers 2" in output
    assert output.endswith("FAILED\n")


def test_main__server_that_is_not_there(capsys: pytest.CaptureFixture[str]) -> None:
    status = main_module.main(argv=["http://127.0.0.1:1"])

    assert status == 1
    assert "got no answer" in capsys.readouterr().out


def test_main__address_that_is_no_http_url(capsys: pytest.CaptureFixture[str]) -> None:
    """A person reads a message, not a traceback."""
    status = main_module.main(argv=["127.0.0.1:8080"])

    assert status == 1
    assert capsys.readouterr().out == (
        "base_url must start with http:// or https://, got '127.0.0.1:8080'.\n"
    )


def test_main__api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """A key on the command line stays in the history of the terminal, so read one too."""
    app = create_app(embedder=FakeEmbedder(), api_key=API_KEY)
    with helpers.serving(app=app) as url:
        assert main_module.main(argv=[url]) == 1
        assert main_module.main(argv=[url, "--api-key", API_KEY]) == 0
        monkeypatch.setenv(main_module.API_KEY_VARIABLE, API_KEY)
        assert main_module.main(argv=[url]) == 0


def _rows(output: str) -> set[str]:
    """The lines of a report, with the padding that lines the columns up removed."""
    return {" ".join(line.split()) for line in output.splitlines()}
