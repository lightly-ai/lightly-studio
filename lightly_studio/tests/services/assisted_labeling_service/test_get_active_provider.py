from __future__ import annotations

import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.assisted_labeling.fake_provider import FakeProvider
from lightly_studio.assisted_labeling.provider import ProviderUnavailableError
from lightly_studio.services.assisted_labeling_service import get_active_provider
from tests.services.assisted_labeling_service import helpers


def test_get_active_provider(db_session: Session) -> None:
    helpers.select_provider(session=db_session, provider_id="fake")

    provider = get_active_provider.get_active_provider(session=db_session)

    assert provider.provider_id == "fake"


def test_get_active_provider__default(db_session: Session) -> None:
    provider = get_active_provider.get_active_provider(session=db_session)

    assert provider.provider_id == "fal_sam3"


def test_get_active_provider__unknown(db_session: Session) -> None:
    helpers.select_provider(session=db_session, provider_id="unknown")

    with pytest.raises(ValueError, match="Unknown assisted labeling provider 'unknown'"):
        get_active_provider.get_active_provider(session=db_session)


def test_get_usable_provider(db_session: Session) -> None:
    helpers.select_provider(session=db_session, provider_id="fake")

    provider = get_active_provider.get_usable_provider(session=db_session)

    assert provider.provider_id == "fake"


def test_get_usable_provider__unavailable(db_session: Session, mocker: MockerFixture) -> None:
    helpers.select_provider(session=db_session, provider_id="fake")
    mocker.patch.object(FakeProvider, "is_available", return_value="Set the API key.")

    with pytest.raises(ProviderUnavailableError, match=r"Set the API key\."):
        get_active_provider.get_usable_provider(session=db_session)
