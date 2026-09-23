from __future__ import annotations

import pytest

from lightly_studio_serve import cli, server
from tests.conformance import helpers
from tests.conformance.helpers import FakeEmbedder

API_KEY = "the-key"


def test_main(capsys: pytest.CaptureFixture[str]) -> None:
    """The server of this package passes over a real socket, which is what CI runs."""
    with helpers.serving(app=server.create_app(embedder=FakeEmbedder())) as url:
        status = cli.main(argv=["conformance", url])

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
        status = cli.main(argv=["conformance", url])

    output = capsys.readouterr().out
    assert status == 1
    assert "text failed" in _rows(output=output)
    assert "answers dimension 3, /v1/describe answers 2" in output
    assert output.endswith("FAILED\n")


def test_main__server_that_is_not_there(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(argv=["conformance", "http://127.0.0.1:1"])

    assert status == 1
    assert "got no answer" in capsys.readouterr().out


def test_main__address_that_is_no_http_url(capsys: pytest.CaptureFixture[str]) -> None:
    """A person reads a message, not a traceback."""
    status = cli.main(argv=["conformance", "127.0.0.1:8080"])

    assert status == 1
    assert capsys.readouterr().out == (
        "base_url must start with http:// or https://, got '127.0.0.1:8080'.\n"
    )


@pytest.mark.parametrize("timeout", ["0", "-1", "nan", "inf"])
def test_main__probe_timeout_that_is_no_number_of_seconds(timeout: str) -> None:
    """A socket refuses these, and every probe would fail under the rest."""
    with pytest.raises(SystemExit):
        cli.main(argv=["conformance", "http://127.0.0.1:1", "--probe-timeout", timeout])


def test_main__api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """A key on the command line stays in the history of the terminal, so read one too."""
    # A key in the environment of the person who runs the tests is no default here.
    monkeypatch.delenv(cli.API_KEY_VARIABLE, raising=False)
    app = server.create_app(embedder=FakeEmbedder(), api_key=API_KEY)
    with helpers.serving(app=app) as url:
        assert cli.main(argv=["conformance", url]) == 1
        assert cli.main(argv=["conformance", url, "--api-key", API_KEY]) == 0
        monkeypatch.setenv(cli.API_KEY_VARIABLE, API_KEY)
        assert cli.main(argv=["conformance", url]) == 0


def test_main__no_command(capsys: pytest.CaptureFixture[str]) -> None:
    """A bare call names the commands rather than running one."""
    with pytest.raises(SystemExit):
        cli.main(argv=[])

    assert "conformance" in capsys.readouterr().err


def _rows(output: str) -> set[str]:
    """The lines of a report, with the padding that lines the columns up removed."""
    return {" ".join(line.split()) for line in output.splitlines()}
