from __future__ import annotations

from uuid import uuid4

import pytest
from sqlmodel import Session

from lightly_studio.models.export_job import ExportType
from lightly_studio.resolvers import export_job_resolver
from tests.helpers_resolvers import create_collection


def test_get_and_validate(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    export_key = export_job_resolver.create(
        session=db_session,
        collection_id=collection.collection_id,
        export_type=ExportType.CAPTIONS,
        filter_json={"image_filter": None},
    )

    result = export_job_resolver.get_and_validate(
        session=db_session,
        export_key=export_key,
        collection_id=collection.collection_id,
        export_type=ExportType.CAPTIONS,
    )

    assert result.export_key == export_key
    assert result.collection_id == collection.collection_id
    assert result.export_type == ExportType.CAPTIONS


def test_get_and_validate__not_found(db_session: Session) -> None:
    with pytest.raises(LookupError):
        export_job_resolver.get_and_validate(
            session=db_session,
            export_key=uuid4(),
            collection_id=uuid4(),
            export_type=ExportType.CAPTIONS,
        )


def test_get_and_validate__wrong_collection(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    export_key = export_job_resolver.create(
        session=db_session,
        collection_id=collection.collection_id,
        export_type=ExportType.CAPTIONS,
        filter_json={"image_filter": None},
    )

    with pytest.raises(ValueError, match="does not belong to this collection"):
        export_job_resolver.get_and_validate(
            session=db_session,
            export_key=export_key,
            collection_id=uuid4(),
            export_type=ExportType.CAPTIONS,
        )


def test_get_and_validate__wrong_export_type(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    export_key = export_job_resolver.create(
        session=db_session,
        collection_id=collection.collection_id,
        export_type=ExportType.CAPTIONS,
        filter_json={"image_filter": None},
    )

    with pytest.raises(ValueError, match="not valid for this export type"):
        export_job_resolver.get_and_validate(
            session=db_session,
            export_key=export_key,
            collection_id=collection.collection_id,
            export_type=ExportType.ANNOTATIONS,
        )
