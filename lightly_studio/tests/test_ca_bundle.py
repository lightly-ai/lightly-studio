"""Tests for custom CA bundle files."""

from __future__ import annotations

import os
import stat
import sys
import tempfile
from collections.abc import Generator
from pathlib import Path

import certifi
import pytest
from pytest_mock import MockerFixture

from lightly_studio import ca_bundle
from tests import helpers_tls

_DEFAULT_BUNDLE = "-----DEFAULT BUNDLE-----\n"


@pytest.fixture(autouse=True)
def _isolate_ca_bundle_files(
    mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Generator[None, None, None]:
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    default_bundle = tmp_path / "default.pem"
    default_bundle.write_text(_DEFAULT_BUNDLE)
    mocker.patch.object(certifi, "where", return_value=str(default_bundle))
    mocker.patch.object(ca_bundle, "_written_files", [])
    yield
    ca_bundle.delete_ca_bundles(keep=None)


@pytest.fixture(scope="module")
def ca_pem() -> str:
    return helpers_tls.create_ca(common_name="Test Root CA").certificate_pem()


def test_write_ca_bundle(ca_pem: str) -> None:
    path = ca_bundle.write_ca_bundle(pem=ca_pem)

    assert Path(path).read_text() == _DEFAULT_BUNDLE + ca_pem


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX file modes only")
def test_write_ca_bundle__file_is_private(ca_pem: str) -> None:
    path = ca_bundle.write_ca_bundle(pem=ca_pem)

    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600


def test_write_ca_bundle__keeps_only_certificate_blocks(ca_pem: str) -> None:
    pem_with_text = f"Subject: Test Root CA\r\n{ca_pem}trailing text\n"

    path = ca_bundle.write_ca_bundle(pem=pem_with_text)

    assert Path(path).read_text() == _DEFAULT_BUNDLE + ca_pem


def test_write_ca_bundle__ignores_unterminated_certificate_block(ca_pem: str) -> None:
    pem = f"-----BEGIN CERTIFICATE-----\nbm90IGVuZGVk\n{ca_pem}"

    path = ca_bundle.write_ca_bundle(pem=pem)

    assert Path(path).read_text() == _DEFAULT_BUNDLE + ca_pem


def test_write_ca_bundle__multiple_certificates() -> None:
    root = helpers_tls.create_ca(common_name="Test Root CA")
    intermediate = helpers_tls.create_ca(common_name="Test Issuing CA", issuer=root)
    pem = intermediate.certificate_pem() + root.certificate_pem()

    path = ca_bundle.write_ca_bundle(pem=pem)

    assert Path(path).read_text() == _DEFAULT_BUNDLE + pem


def test_write_ca_bundle__uses_requests_ca_bundle_as_default(
    ca_pem: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    requests_bundle = tmp_path / "corporate.pem"
    requests_bundle.write_text("-----CORPORATE BUNDLE-----\n")
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(requests_bundle))

    path = ca_bundle.write_ca_bundle(pem=ca_pem)

    assert Path(path).read_text() == "-----CORPORATE BUNDLE-----\n" + ca_pem


def test_write_ca_bundle__ignores_requests_ca_bundle_directory(
    ca_pem: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(tmp_path))

    path = ca_bundle.write_ca_bundle(pem=ca_pem)

    assert Path(path).read_text() == _DEFAULT_BUNDLE + ca_pem


def test_write_ca_bundle__rejects_too_large_bundle(ca_pem: str) -> None:
    pem = ca_pem + "x" * 64 * 1024

    with pytest.raises(ValueError, match="larger than 64 KiB"):
        ca_bundle.write_ca_bundle(pem=pem)


def test_write_ca_bundle__rejects_private_key() -> None:
    ca = helpers_tls.create_ca(common_name="Test Root CA")

    with pytest.raises(ValueError, match="private key"):
        ca_bundle.write_ca_bundle(pem=ca.certificate_pem() + ca.key_pem())


def test_write_ca_bundle__rejects_text_without_certificate() -> None:
    with pytest.raises(ValueError, match="no PEM certificate"):
        ca_bundle.write_ca_bundle(pem="not a certificate")


def test_write_ca_bundle__rejects_invalid_certificate() -> None:
    pem = "-----BEGIN CERTIFICATE-----\nbm90IGEgY2VydGlmaWNhdGU=\n-----END CERTIFICATE-----\n"

    with pytest.raises(ValueError, match="invalid certificate"):
        ca_bundle.write_ca_bundle(pem=pem)


def test_write_ca_bundle__rejected_bundle_writes_no_file(tmp_path: Path) -> None:
    files_before = set(tmp_path.iterdir())

    with pytest.raises(ValueError, match="no PEM certificate"):
        ca_bundle.write_ca_bundle(pem="not a certificate")

    assert set(tmp_path.iterdir()) == files_before


def test_write_ca_bundle__failed_write_is_deleted_on_cleanup(
    ca_pem: str, mocker: MockerFixture, tmp_path: Path
) -> None:
    files_before = set(tmp_path.iterdir())
    # A lone surrogate cannot be encoded as UTF-8, so the write fails after the file exists.
    mocker.patch.object(ca_bundle, "_read_default_ca_bundle", return_value="\ud800")
    with pytest.raises(UnicodeEncodeError):
        ca_bundle.write_ca_bundle(pem=ca_pem)

    ca_bundle.delete_ca_bundles(keep=None)

    assert set(tmp_path.iterdir()) == files_before


def test_delete_ca_bundles__keeps_given_file(ca_pem: str) -> None:
    other_pem = helpers_tls.create_ca(common_name="Other Root CA").certificate_pem()
    old_path = ca_bundle.write_ca_bundle(pem=ca_pem)
    new_path = ca_bundle.write_ca_bundle(pem=other_pem)

    ca_bundle.delete_ca_bundles(keep=new_path)

    assert not os.path.exists(old_path)
    assert os.path.exists(new_path)


def test_delete_ca_bundles__deletes_all_files(ca_pem: str) -> None:
    path = ca_bundle.write_ca_bundle(pem=ca_pem)

    ca_bundle.delete_ca_bundles(keep=None)

    assert not os.path.exists(path)
    assert ca_bundle._written_files == []


def test_delete_ca_bundles__ignores_missing_file(ca_pem: str) -> None:
    path = ca_bundle.write_ca_bundle(pem=ca_pem)
    os.remove(path)

    ca_bundle.delete_ca_bundles(keep=None)

    assert ca_bundle._written_files == []
