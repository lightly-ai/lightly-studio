"""Tests for applying cloud storage credentials."""

from __future__ import annotations

import json
import os
import ssl
import tempfile
import threading
from collections.abc import Generator
from pathlib import Path

import fsspec
import pytest
from adlfs import AzureBlobFileSystem  # type: ignore[import-untyped]
from botocore.exceptions import EndpointConnectionError
from gcsfs import GCSFileSystem  # type: ignore[import-untyped]
from moto.moto_server.werkzeug_app import DomainDispatcherApplication, create_backend_app
from pytest_mock import MockerFixture
from werkzeug.serving import make_server

from lightly_studio import ca_bundle, cloud_credentials
from lightly_studio.cloud_credentials import apply_cloud_credentials
from tests import helpers_tls


@pytest.fixture(autouse=True)
def _reset_cloud_configuration(mocker: MockerFixture) -> Generator[None, None, None]:
    mocker.patch.dict(os.environ, {}, clear=True)
    mocker.patch.dict(fsspec.config.conf, {}, clear=True)
    AzureBlobFileSystem.clear_instance_cache()
    GCSFileSystem.clear_instance_cache()
    yield
    AzureBlobFileSystem.clear_instance_cache()
    GCSFileSystem.clear_instance_cache()


@pytest.fixture(autouse=True)
def _isolate_ca_bundle_files(
    mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Generator[None, None, None]:
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    mocker.patch.object(ca_bundle, "_written_files", [])
    yield
    ca_bundle.delete_ca_bundles(keep=None)


@pytest.fixture(scope="module")
def private_root_ca() -> helpers_tls.CertificateWithKey:
    return helpers_tls.create_ca(common_name="Test Root CA")


@pytest.fixture(scope="module")
def private_issuing_ca(
    private_root_ca: helpers_tls.CertificateWithKey,
) -> helpers_tls.CertificateWithKey:
    return helpers_tls.create_ca(common_name="Test Issuing CA", issuer=private_root_ca)


@pytest.fixture
def private_s3_endpoint(
    private_issuing_ca: helpers_tls.CertificateWithKey, tmp_path: Path
) -> Generator[str, None, None]:
    """Run a moto S3 server over TLS that sends only its leaf certificate.

    The server does not send the issuing CA, so clients must have it in their CA bundle.
    """
    leaf = helpers_tls.create_server_certificate(issuer=private_issuing_ca, host="localhost")
    certificate_path = tmp_path / "server.pem"
    key_path = tmp_path / "server.key"
    certificate_path.write_text(leaf.certificate_pem())
    key_path.write_text(leaf.key_pem())
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(certfile=certificate_path, keyfile=key_path)

    server = make_server(
        host="localhost",
        port=0,
        app=DomainDispatcherApplication(create_backend_app),
        threaded=True,
        ssl_context=ssl_context,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"https://localhost:{server.port}"
    server.shutdown()
    thread.join()


def test_apply_cloud_credentials__applies_gcs_runtime_config(
    mocker: MockerFixture,
) -> None:
    storage_options = {
        "project": "test-project",
        "token": {
            "type": "service_account",
            "client_email": "studio@test-project.iam.gserviceaccount.com",
        },
    }
    serialized_options = json.dumps(storage_options)
    clear_cache = mocker.spy(GCSFileSystem, "clear_instance_cache")

    apply_cloud_credentials(credentials={"FSSPEC_GCS": serialized_options})

    assert os.environ["FSSPEC_GCS"] == serialized_options
    assert fsspec.config.conf["gcs"] == storage_options
    clear_cache.assert_called_once_with()


def test_apply_cloud_credentials__invalidates_cached_gcs_filesystem() -> None:
    apply_cloud_credentials(
        credentials={"FSSPEC_GCS": json.dumps({"project": "old-project", "token": "anon"})}
    )
    old_filesystem = fsspec.filesystem("gcs")
    assert GCSFileSystem._cache
    assert fsspec.filesystem("gcs") is old_filesystem

    apply_cloud_credentials(
        credentials={"FSSPEC_GCS": json.dumps({"project": "new-project", "token": "anon"})}
    )

    assert not GCSFileSystem._cache
    new_filesystem = fsspec.filesystem("gcs")
    assert new_filesystem is not old_filesystem
    assert new_filesystem.project == "new-project"


def test_apply_cloud_credentials__replaces_removed_gcs_options() -> None:
    fsspec.config.conf["gcs"] = {
        "project": "old-project",
        "token": "old-token",
    }

    apply_cloud_credentials(credentials={"FSSPEC_GCS": json.dumps({"token": "new-token"})})

    assert fsspec.config.conf["gcs"] == {"token": "new-token"}


def test_apply_cloud_credentials__applies_azure_runtime_config(
    mocker: MockerFixture,
) -> None:
    storage_options = {"account_name": "test-account", "account_key": "test-key"}
    serialized_options = json.dumps(storage_options)
    clear_cache = mocker.spy(AzureBlobFileSystem, "clear_instance_cache")

    apply_cloud_credentials(credentials={"FSSPEC_ABFS": serialized_options})

    assert os.environ["FSSPEC_ABFS"] == serialized_options
    assert fsspec.config.conf["abfs"] == storage_options
    assert fsspec.filesystem("az").account_name == "test-account"
    clear_cache.assert_called_once_with()


def test_apply_cloud_credentials__supports_legacy_fsspec_config_parser(
    mocker: MockerFixture,
) -> None:
    storage_options = {"account_name": "test-account", "account_key": "test-key"}
    mocker.patch.object(fsspec.config, "set_conf_env")

    apply_cloud_credentials(credentials={"FSSPEC_ABFS": json.dumps(storage_options)})

    assert fsspec.config.conf["abfs"] == storage_options


def test_apply_cloud_credentials__invalidates_cached_azure_filesystem() -> None:
    apply_cloud_credentials(
        credentials={
            "FSSPEC_ABFS": json.dumps({"account_name": "old-account", "account_key": "old-key"})
        }
    )
    old_filesystem = fsspec.filesystem("abfs")
    assert AzureBlobFileSystem._cache
    assert fsspec.filesystem("az") is old_filesystem

    apply_cloud_credentials(
        credentials={
            "FSSPEC_ABFS": json.dumps({"account_name": "new-account", "account_key": "new-key"})
        }
    )

    assert not AzureBlobFileSystem._cache
    new_filesystem = fsspec.filesystem("az")
    assert new_filesystem is not old_filesystem
    assert new_filesystem.account_name == "new-account"


@pytest.mark.parametrize("value", ["not-json", "[]"])
def test_apply_cloud_credentials__rejects_invalid_fsspec_config(value: str) -> None:
    with pytest.raises(ValueError, match="Invalid FSSPEC cloud credential configuration"):
        apply_cloud_credentials(credentials={"FSSPEC_GCS": value})

    assert "FSSPEC_GCS" not in os.environ
    assert "gcs" not in fsspec.config.conf


def test_apply_cloud_credentials__missing_filesystem_dependency(
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        fsspec,
        "get_filesystem_class",
        side_effect=ImportError("No module named 'gcsfs'"),
    )

    with pytest.raises(ImportError, match="lightly-studio"):
        apply_cloud_credentials(credentials={"FSSPEC_GCS": json.dumps({"token": "anon"})})

    assert "FSSPEC_GCS" not in os.environ
    assert "gcs" not in fsspec.config.conf


def test_apply_cloud_credentials__writes_ca_bundle(
    private_root_ca: helpers_tls.CertificateWithKey,
) -> None:
    ca_pem = private_root_ca.certificate_pem()

    apply_cloud_credentials(
        credentials={"AWS_ACCESS_KEY_ID": "key", "AWS_CA_BUNDLE_PEM": ca_pem},
    )

    assert "AWS_CA_BUNDLE_PEM" not in os.environ
    assert os.environ["AWS_ACCESS_KEY_ID"] == "key"
    assert Path(os.environ["AWS_CA_BUNDLE"]).read_text().endswith(ca_pem)


def test_apply_cloud_credentials__without_ca_bundle_writes_no_file(tmp_path: Path) -> None:
    apply_cloud_credentials(
        credentials={"AWS_ACCESS_KEY_ID": "key", "AWS_SECRET_ACCESS_KEY": "secret"},
    )

    assert "AWS_CA_BUNDLE" not in os.environ
    assert list(tmp_path.iterdir()) == []


def test_apply_cloud_credentials__removes_ca_bundle_on_rotation(
    private_root_ca: helpers_tls.CertificateWithKey,
) -> None:
    apply_cloud_credentials(
        credentials={
            "AWS_ACCESS_KEY_ID": "key",
            "AWS_CA_BUNDLE_PEM": private_root_ca.certificate_pem(),
        },
    )
    old_ca_bundle_path = os.environ["AWS_CA_BUNDLE"]

    apply_cloud_credentials(credentials={"AWS_ACCESS_KEY_ID": "new-key"})

    assert "AWS_CA_BUNDLE" not in os.environ
    assert not os.path.exists(old_ca_bundle_path)


def test_apply_cloud_credentials__replaces_ca_bundle(
    private_root_ca: helpers_tls.CertificateWithKey,
    private_issuing_ca: helpers_tls.CertificateWithKey,
) -> None:
    apply_cloud_credentials(
        credentials={
            "AWS_ACCESS_KEY_ID": "key",
            "AWS_CA_BUNDLE_PEM": private_root_ca.certificate_pem(),
        },
    )
    old_ca_bundle_path = os.environ["AWS_CA_BUNDLE"]

    apply_cloud_credentials(
        credentials={
            "AWS_ACCESS_KEY_ID": "key",
            "AWS_CA_BUNDLE_PEM": private_issuing_ca.certificate_pem(),
        },
    )

    new_ca_bundle_path = os.environ["AWS_CA_BUNDLE"]
    assert new_ca_bundle_path != old_ca_bundle_path
    assert not os.path.exists(old_ca_bundle_path)
    assert Path(new_ca_bundle_path).read_text().endswith(private_issuing_ca.certificate_pem())


def test_apply_cloud_credentials__keeps_ca_bundle_on_other_provider_refresh(
    private_root_ca: helpers_tls.CertificateWithKey,
) -> None:
    apply_cloud_credentials(
        credentials={
            "AWS_ACCESS_KEY_ID": "key",
            "AWS_CA_BUNDLE_PEM": private_root_ca.certificate_pem(),
        },
    )
    ca_bundle_path = os.environ["AWS_CA_BUNDLE"]

    apply_cloud_credentials(credentials={"FSSPEC_GCS": json.dumps({"token": "anon"})})

    assert os.environ["AWS_CA_BUNDLE"] == ca_bundle_path
    assert os.path.exists(ca_bundle_path)


def test_apply_cloud_credentials__rejects_invalid_ca_bundle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "old-key")

    with pytest.raises(ValueError, match="no PEM certificate"):
        apply_cloud_credentials(
            credentials={"AWS_ACCESS_KEY_ID": "new-key", "AWS_CA_BUNDLE_PEM": "not a certificate"},
        )

    assert os.environ["AWS_ACCESS_KEY_ID"] == "old-key"
    assert "AWS_CA_BUNDLE" not in os.environ


def test_apply_cloud_credentials__rejects_ca_bundle_path_and_pem(
    private_root_ca: helpers_tls.CertificateWithKey,
) -> None:
    with pytest.raises(ValueError, match="cannot be used together"):
        apply_cloud_credentials(
            credentials={
                "AWS_CA_BUNDLE": "/path/to/bundle.pem",
                "AWS_CA_BUNDLE_PEM": private_root_ca.certificate_pem(),
            },
        )

    assert "AWS_CA_BUNDLE" not in os.environ


def test_apply_cloud_credentials__ca_bundle_trusts_private_s3_endpoint(
    private_root_ca: helpers_tls.CertificateWithKey,
    private_issuing_ca: helpers_tls.CertificateWithKey,
    private_s3_endpoint: str,
) -> None:
    credentials = {
        "AWS_ACCESS_KEY_ID": "testing",
        "AWS_SECRET_ACCESS_KEY": "testing",
        "AWS_DEFAULT_REGION": "us-east-1",
        "AWS_ENDPOINT_URL_S3": private_s3_endpoint,
        # Fail fast on the TLS error instead of retrying.
        "AWS_MAX_ATTEMPTS": "1",
    }
    apply_cloud_credentials(credentials=credentials)
    with pytest.raises(EndpointConnectionError):
        fsspec.filesystem("s3").ls("")

    ca_pem = private_issuing_ca.certificate_pem() + private_root_ca.certificate_pem()
    apply_cloud_credentials(credentials={**credentials, "AWS_CA_BUNDLE_PEM": ca_pem})
    filesystem = fsspec.filesystem("s3")
    filesystem.mkdir("ca-test")

    assert filesystem.ls("") == ["ca-test"]


def test_apply_cloud_credentials__serializes_concurrent_calls(
    mocker: MockerFixture,
    private_root_ca: helpers_tls.CertificateWithKey,
    private_issuing_ca: helpers_tls.CertificateWithKey,
) -> None:
    write_started = threading.Event()
    release_write = threading.Event()
    write_ca_bundle = ca_bundle.write_ca_bundle

    def write_ca_bundle_and_block_first_call(pem: str) -> str:
        if not write_started.is_set():
            write_started.set()
            release_write.wait()
        return write_ca_bundle(pem=pem)

    mocker.patch.object(
        ca_bundle, "write_ca_bundle", side_effect=write_ca_bundle_and_block_first_call
    )
    first = threading.Thread(
        target=apply_cloud_credentials,
        kwargs={
            "credentials": {
                "AWS_ACCESS_KEY_ID": "first",
                "AWS_CA_BUNDLE_PEM": private_root_ca.certificate_pem(),
            }
        },
    )
    second = threading.Thread(
        target=apply_cloud_credentials,
        kwargs={
            "credentials": {
                "AWS_ACCESS_KEY_ID": "second",
                "AWS_CA_BUNDLE_PEM": private_issuing_ca.certificate_pem(),
            }
        },
    )

    first.start()
    write_started.wait()
    second.start()
    second.join(timeout=0.2)
    second_waited = second.is_alive()
    release_write.set()
    first.join()
    second.join()

    # The second call waits until the first call is complete.
    assert second_waited
    assert os.environ["AWS_ACCESS_KEY_ID"] == "second"
    assert (
        Path(os.environ["AWS_CA_BUNDLE"]).read_text().endswith(private_issuing_ca.certificate_pem())
    )


def test_validate_credential_keys__accepts_aws_keys() -> None:
    cloud_credentials._validate_credential_keys(
        credentials={
            "AWS_ACCESS_KEY_ID": "key",
            "AWS_SECRET_ACCESS_KEY": "secret",
            "AWS_SESSION_TOKEN": "token",
        }
    )


def test_validate_credential_keys__accepts_google_credentials() -> None:
    cloud_credentials._validate_credential_keys(
        credentials={"GOOGLE_APPLICATION_CREDENTIALS": "/path/to/key.json"}
    )


def test_validate_credential_keys__accepts_fsspec_keys() -> None:
    cloud_credentials._validate_credential_keys(
        credentials={"FSSPEC_S3_KEY": "key", "FSSPEC_S3_SECRET": "secret"}
    )


def test_validate_credential_keys__rejects_arbitrary_key() -> None:
    with pytest.raises(ValueError, match="EVIL_KEY"):
        cloud_credentials._validate_credential_keys(credentials={"EVIL_KEY": "value"})


def test_validate_credential_keys__rejects_mixed_keys() -> None:
    with pytest.raises(ValueError, match="EVIL_KEY"):
        cloud_credentials._validate_credential_keys(
            credentials={"AWS_ACCESS_KEY_ID": "key", "EVIL_KEY": "value"}
        )


def test_validate_credential_keys__rejects_path_traversal_key() -> None:
    with pytest.raises(ValueError, match="PATH"):
        cloud_credentials._validate_credential_keys(credentials={"PATH": "/usr/bin:/usr/local/bin"})


def test_validate_credential_keys__rejects_http_proxy_key() -> None:
    with pytest.raises(ValueError, match="HTTP_PROXY"):
        cloud_credentials._validate_credential_keys(
            credentials={"HTTP_PROXY": "http://attacker.example/"}
        )


def test_remove_stale_provider_env_vars__drops_omitted_aws_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "token")

    # Rotation payload does not include AWS_SESSION_TOKEN.
    cloud_credentials._remove_stale_provider_env_vars(
        credentials={"AWS_ACCESS_KEY_ID": "new-key", "AWS_SECRET_ACCESS_KEY": "new-secret"}
    )

    assert "AWS_ACCESS_KEY_ID" not in os.environ
    assert "AWS_SECRET_ACCESS_KEY" not in os.environ
    assert "AWS_SESSION_TOKEN" not in os.environ


def test_remove_stale_provider_env_vars__does_not_touch_other_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "key")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/path/to/key.json")

    # AWS-only payload — GCS variable must be left alone.
    cloud_credentials._remove_stale_provider_env_vars(credentials={"AWS_ACCESS_KEY_ID": "new-key"})

    assert "AWS_ACCESS_KEY_ID" not in os.environ
    assert os.environ["GOOGLE_APPLICATION_CREDENTIALS"] == "/path/to/key.json"


def test_remove_stale_provider_env_vars__drops_omitted_fsspec_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FSSPEC_S3_KEY", "key")
    monkeypatch.setenv("FSSPEC_S3_SECRET", "secret")
    monkeypatch.setenv("FSSPEC_S3_TOKEN", "token")

    # Rotation payload does not include FSSPEC_S3_TOKEN.
    cloud_credentials._remove_stale_provider_env_vars(
        credentials={"FSSPEC_S3_KEY": "new-key", "FSSPEC_S3_SECRET": "new-secret"}
    )

    assert "FSSPEC_S3_KEY" not in os.environ
    assert "FSSPEC_S3_SECRET" not in os.environ
    assert "FSSPEC_S3_TOKEN" not in os.environ


def test_remove_stale_provider_env_vars__fsspec_only_does_not_touch_other_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FSSPEC_S3_KEY", "key")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "aws-key")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/path/to/key.json")

    # FSSPEC-only payload — AWS and GCS variables must be left alone.
    cloud_credentials._remove_stale_provider_env_vars(credentials={"FSSPEC_S3_KEY": "new-key"})

    assert "FSSPEC_S3_KEY" not in os.environ
    assert os.environ["AWS_ACCESS_KEY_ID"] == "aws-key"
    assert os.environ["GOOGLE_APPLICATION_CREDENTIALS"] == "/path/to/key.json"
