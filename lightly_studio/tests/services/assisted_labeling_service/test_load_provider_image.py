from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlmodel import Session

from lightly_studio.errors import NotFoundError
from lightly_studio.services import assisted_labeling_service
from tests.helpers_resolvers import create_collection, create_image


def test_load_provider_image(db_session: Session, tmp_path: Path) -> None:
    file_path = tmp_path / "img.png"
    file_path.write_bytes(b"image data")
    collection = create_collection(session=db_session)
    image = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs=str(file_path),
        width=100,
        height=50,
    )

    provider_image = assisted_labeling_service.load_provider_image(
        session=db_session, collection_id=collection.collection_id, sample_id=image.sample_id
    )

    assert provider_image.sample_id == image.sample_id
    assert provider_image.width == 100
    assert provider_image.height == 50
    assert provider_image.file_name == "img.png"
    assert provider_image.read_bytes() == b"image data"


def test_load_provider_image__missing_file(db_session: Session, tmp_path: Path) -> None:
    collection = create_collection(session=db_session)
    image = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs=str(tmp_path / "missing.png"),
    )
    provider_image = assisted_labeling_service.load_provider_image(
        session=db_session, collection_id=collection.collection_id, sample_id=image.sample_id
    )

    with pytest.raises(NotFoundError, match="does not exist"):
        provider_image.read_bytes()


def test_load_provider_image__unknown_size(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id, width=0)

    with pytest.raises(ValueError, match="has no known size"):
        assisted_labeling_service.load_provider_image(
            session=db_session, collection_id=collection.collection_id, sample_id=image.sample_id
        )


def test_load_provider_image__unknown_sample(db_session: Session) -> None:
    collection = create_collection(session=db_session)

    with pytest.raises(NotFoundError, match="not found in collection"):
        assisted_labeling_service.load_provider_image(
            session=db_session, collection_id=collection.collection_id, sample_id=uuid.uuid4()
        )


def test_load_provider_image__other_collection(db_session: Session) -> None:
    collection = create_collection(session=db_session, collection_name="first")
    other_collection = create_collection(session=db_session, collection_name="second")
    image = create_image(session=db_session, collection_id=other_collection.collection_id)

    with pytest.raises(NotFoundError, match="not found in collection"):
        assisted_labeling_service.load_provider_image(
            session=db_session, collection_id=collection.collection_id, sample_id=image.sample_id
        )
