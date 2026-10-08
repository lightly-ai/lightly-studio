from __future__ import annotations

from uuid import uuid4

import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.assisted_labeling.fake_provider import FakeProvider
from lightly_studio.assisted_labeling.provider import ProviderUnavailableError
from lightly_studio.errors import NotFoundError
from lightly_studio.models.assisted_labeling import PrepareAnnotationRequest
from lightly_studio.services import assisted_labeling_service
from tests.helpers_resolvers import create_collection, create_image
from tests.services.assisted_labeling_service import helpers


def test_prepare_image(db_session: Session, mocker: MockerFixture) -> None:
    helpers.select_provider(session=db_session, provider_id="fake")
    spy_prepare = mocker.spy(FakeProvider, "prepare")
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)

    assisted_labeling_service.prepare_image(
        session=db_session,
        request=PrepareAnnotationRequest(
            collection_id=collection.collection_id, sample_id=image.sample_id
        ),
    )

    spy_prepare.assert_called_once()
    assert spy_prepare.call_args.kwargs["image"].sample_id == image.sample_id


def test_prepare_image__unknown_sample(db_session: Session) -> None:
    helpers.select_provider(session=db_session, provider_id="fake")
    collection = create_collection(session=db_session)

    with pytest.raises(NotFoundError):
        assisted_labeling_service.prepare_image(
            session=db_session,
            request=PrepareAnnotationRequest(
                collection_id=collection.collection_id, sample_id=uuid4()
            ),
        )


def test_prepare_image__unavailable(db_session: Session, mocker: MockerFixture) -> None:
    helpers.select_provider(session=db_session, provider_id="fake")
    mocker.patch.object(FakeProvider, "is_available", return_value="Set the API key.")
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)

    with pytest.raises(ProviderUnavailableError):
        assisted_labeling_service.prepare_image(
            session=db_session,
            request=PrepareAnnotationRequest(
                collection_id=collection.collection_id, sample_id=image.sample_id
            ),
        )
