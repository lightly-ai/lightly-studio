import os

import pytest

from lightly_studio import cloud_credentials


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
