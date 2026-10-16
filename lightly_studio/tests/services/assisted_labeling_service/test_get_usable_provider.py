from __future__ import annotations

import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.assisted_labeling import fal_sam3_provider, provider_ids
from lightly_studio.assisted_labeling.fake_provider import FakeProvider
from lightly_studio.assisted_labeling.provider import ProviderUnavailableError
from lightly_studio.services import assisted_labeling_service
from tests.services.assisted_labeling_service import helpers


def test_get_usable_provider(db_session: Session) -> None:
    helpers.select_provider(session=db_session, provider_id=provider_ids.FAKE_PROVIDER_ID)

    provider = assisted_labeling_service.get_usable_provider(session=db_session)

    assert provider.provider_id == provider_ids.FAKE_PROVIDER_ID


def test_get_usable_provider__default(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(fal_sam3_provider.FAL_KEY_ENV_VAR, "test-key")

    provider = assisted_labeling_service.get_usable_provider(session=db_session)

    assert provider.provider_id == provider_ids.DEFAULT_PROVIDER_ID


def test_get_usable_provider__unknown(db_session: Session) -> None:
    helpers.select_provider(session=db_session, provider_id="unknown")

    with pytest.raises(ValueError, match="Unknown assisted labeling provider 'unknown'"):
        assisted_labeling_service.get_usable_provider(session=db_session)


def test_get_usable_provider__unavailable(db_session: Session, mocker: MockerFixture) -> None:
    helpers.select_provider(session=db_session, provider_id=provider_ids.FAKE_PROVIDER_ID)
    mocker.patch.object(FakeProvider, "is_available", return_value="Set the API key.")

    with pytest.raises(ProviderUnavailableError, match=r"Set the API key\."):
        assisted_labeling_service.get_usable_provider(session=db_session)
