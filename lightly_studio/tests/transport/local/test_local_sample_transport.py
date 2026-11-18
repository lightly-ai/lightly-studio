from __future__ import annotations

from uuid import uuid4

import pytest

from lightly_studio.database import db_manager
from lightly_studio.errors import NotFoundError
from lightly_studio.models.collection import SampleType
from lightly_studio.models.query_expr import (
    FieldRef,
    IntegerExpr,
    OrdinalComparisonOperator,
    QueryExpr,
)
from lightly_studio.models.sample_query import SampleQueryRequest
from lightly_studio.transport.local.local_sample_transport import LocalSampleTransport
from lightly_studio.transport.sample_transport import SampleTransport
from tests.helpers_resolvers import create_collection, create_image


@pytest.mark.usefixtures("patch_collection")
class TestLocalSampleTransport:
    def test_get_by_ids(self) -> None:
        session = db_manager.persistent_session()
        collection_id = create_collection(session=session).collection_id
        image = create_image(session=session, collection_id=collection_id)
        transport: SampleTransport = LocalSampleTransport()

        samples = transport.get_by_ids(sample_ids=[image.sample_id])

        assert [sample.sample_id for sample in samples] == [image.sample_id]

    def test_query(self) -> None:
        session = db_manager.persistent_session()
        collection_id = create_collection(session=session).collection_id
        for path in ["/a.png", "/b.png"]:
            create_image(session=session, collection_id=collection_id, file_path_abs=path)
        transport: SampleTransport = LocalSampleTransport()

        page = transport.query(collection_id=collection_id, request=SampleQueryRequest(limit=1))

        assert [sample.file_name for sample in page.samples] == ["a.png"]
        assert page.next_cursor is not None

    def test_query__collection_not_found(self) -> None:
        transport: SampleTransport = LocalSampleTransport()

        with pytest.raises(NotFoundError):
            transport.query(collection_id=uuid4(), request=SampleQueryRequest())

    def test_query__not_image_collection(self) -> None:
        session = db_manager.persistent_session()
        collection_id = create_collection(
            session=session, sample_type=SampleType.VIDEO
        ).collection_id
        transport: SampleTransport = LocalSampleTransport()

        with pytest.raises(ValueError, match="only image collections"):
            transport.query(collection_id=collection_id, request=SampleQueryRequest())

    def test_query__unknown_field(self) -> None:
        session = db_manager.persistent_session()
        collection_id = create_collection(session=session).collection_id
        width = FieldRef(table="video", name="width")
        match_expr = IntegerExpr(field=width, operator=OrdinalComparisonOperator.GT, value=1)
        request = SampleQueryRequest(query_expr=QueryExpr(match_expr=match_expr))
        transport: SampleTransport = LocalSampleTransport()

        with pytest.raises(ValueError, match="not valid here"):
            transport.query(collection_id=collection_id, request=request)
