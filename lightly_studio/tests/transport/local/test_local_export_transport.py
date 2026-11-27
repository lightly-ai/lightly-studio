from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy
from pytest_mock import MockerFixture

from lightly_studio.database import db_manager
from lightly_studio.errors import NotFoundError, QueryExprError
from lightly_studio.models.collection import SampleType
from lightly_studio.models.export_format import ExportFormat
from lightly_studio.models.export_task import ExportTask
from lightly_studio.models.query_expr import (
    FieldRef,
    IntegerExpr,
    OrdinalComparisonOperator,
    QueryExpr,
)
from lightly_studio.models.sample_query import SampleQueryRequest, SortKey
from lightly_studio.transport.export_transport import ExportTransport
from lightly_studio.transport.local import local_export_transport
from lightly_studio.transport.local.local_export_transport import LocalExportTransport
from tests.helpers_resolvers import create_collection, create_image


@pytest.mark.usefixtures("patch_collection")
class TestLocalExportTransport:
    def test_export(self, tmp_path: Path) -> None:
        session = db_manager.persistent_session()
        collection_id = create_collection(session=session).collection_id
        create_image(
            session=session, collection_id=collection_id, file_path_abs="/a.png", width=100
        )
        create_image(
            session=session, collection_id=collection_id, file_path_abs="/b.png", width=200
        )
        query_expr = QueryExpr(
            match_expr=IntegerExpr(
                field=FieldRef(table="image", name="width"),
                operator=OrdinalComparisonOperator.GT,
                value=150,
            )
        )
        output_json = tmp_path / "coco.json"
        transport: ExportTransport = LocalExportTransport()

        transport.export(
            collection_id=collection_id,
            request=SampleQueryRequest(query_expr=query_expr),
            limit=None,
            task=ExportTask(
                export_format=ExportFormat.OBJECT_DETECTION_COCO,
                output_path=output_json,
                annotation_collection_id=None,
            ),
        )

        coco = json.loads(output_json.read_text())
        assert [image["file_name"] for image in coco["images"]] == ["/b.png"]

    def test_export__all_samples(self, tmp_path: Path) -> None:
        session = db_manager.persistent_session()
        collection_id = create_collection(session=session).collection_id
        create_image(session=session, collection_id=collection_id, file_path_abs="/a.png")
        create_image(session=session, collection_id=collection_id, file_path_abs="/b.png")
        output_json = tmp_path / "coco.json"

        LocalExportTransport().export(
            collection_id=collection_id,
            request=SampleQueryRequest(),
            limit=None,
            task=ExportTask(
                export_format=ExportFormat.OBJECT_DETECTION_COCO,
                output_path=output_json,
                annotation_collection_id=None,
            ),
        )

        coco = json.loads(output_json.read_text())
        assert [image["file_name"] for image in coco["images"]] == ["/a.png", "/b.png"]

    def test_export__sort_and_slice(self, tmp_path: Path) -> None:
        session = db_manager.persistent_session()
        collection_id = create_collection(session=session).collection_id
        for path, width in [("/a.png", 300), ("/b.png", 100), ("/c.png", 200), ("/d.png", 400)]:
            create_image(
                session=session, collection_id=collection_id, file_path_abs=path, width=width
            )
        output_json = tmp_path / "coco.json"

        LocalExportTransport().export(
            collection_id=collection_id,
            request=SampleQueryRequest(
                sort=[SortKey(field=FieldRef(table="image", name="width"))], offset=1
            ),
            limit=2,
            task=ExportTask(
                export_format=ExportFormat.OBJECT_DETECTION_COCO,
                output_path=output_json,
                annotation_collection_id=None,
            ),
        )

        coco = json.loads(output_json.read_text())
        assert [image["file_name"] for image in coco["images"]] == ["/c.png", "/a.png"]

    def test_export__statement_count(self, mocker: MockerFixture, tmp_path: Path) -> None:
        session = db_manager.persistent_session()
        collection_id = create_collection(session=session).collection_id

        def count_statements() -> int:
            session.expire_all()
            listener = mocker.Mock()
            engine = session.get_bind()
            sqlalchemy.event.listen(engine, "before_cursor_execute", listener)
            try:
                LocalExportTransport().export(
                    collection_id=collection_id,
                    request=SampleQueryRequest(),
                    limit=None,
                    task=ExportTask(
                        export_format=ExportFormat.OBJECT_DETECTION_COCO,
                        output_path=tmp_path / "coco.json",
                        annotation_collection_id=None,
                    ),
                )
            finally:
                sqlalchemy.event.remove(engine, "before_cursor_execute", listener)
            return int(listener.call_count)

        create_image(session=session, collection_id=collection_id, file_path_abs="/a.png")
        one_image_count = count_statements()
        create_image(session=session, collection_id=collection_id, file_path_abs="/b.png")
        create_image(session=session, collection_id=collection_id, file_path_abs="/c.png")

        assert count_statements() == one_image_count

    def test_export__annotation_collection_id(self, mocker: MockerFixture, tmp_path: Path) -> None:
        session = db_manager.persistent_session()
        collection_id = create_collection(session=session).collection_id
        annotation_collection_id = uuid4()
        export_samples = mocker.MagicMock()
        mocker.patch.dict(
            local_export_transport._IMAGE_EXPORTS,
            {ExportFormat.OBJECT_DETECTION_COCO: export_samples},
        )

        LocalExportTransport().export(
            collection_id=collection_id,
            request=SampleQueryRequest(),
            limit=None,
            task=ExportTask(
                export_format=ExportFormat.OBJECT_DETECTION_COCO,
                output_path=tmp_path / "coco.json",
                annotation_collection_id=annotation_collection_id,
            ),
        )

        export_samples.assert_called_once_with(
            mocker.ANY, tmp_path / "coco.json", annotation_collection_id
        )

    def test_export__field_of_other_table(self, tmp_path: Path) -> None:
        session = db_manager.persistent_session()
        collection_id = create_collection(session=session).collection_id
        query_expr = QueryExpr(
            match_expr=IntegerExpr(
                field=FieldRef(table="video", name="width"),
                operator=OrdinalComparisonOperator.GT,
                value=150,
            )
        )

        with pytest.raises(QueryExprError, match=r"video.width is not valid here"):
            LocalExportTransport().export(
                collection_id=collection_id,
                request=SampleQueryRequest(query_expr=query_expr),
                limit=None,
                task=ExportTask(
                    export_format=ExportFormat.OBJECT_DETECTION_COCO,
                    output_path=tmp_path / "coco.json",
                    annotation_collection_id=None,
                ),
            )

    def test_export__format_not_for_images(self, tmp_path: Path) -> None:
        session = db_manager.persistent_session()
        collection_id = create_collection(session=session).collection_id

        with pytest.raises(ValueError, match=r"'youtube_vis_segmentation' is not supported"):
            LocalExportTransport().export(
                collection_id=collection_id,
                request=SampleQueryRequest(),
                limit=None,
                task=ExportTask(
                    export_format=ExportFormat.YOUTUBE_VIS_SEGMENTATION,
                    output_path=tmp_path / "export.json",
                    annotation_collection_id=None,
                ),
            )

    def test_export__video_collection(self, tmp_path: Path) -> None:
        session = db_manager.persistent_session()
        collection_id = create_collection(
            session=session, sample_type=SampleType.VIDEO
        ).collection_id

        with pytest.raises(ValueError, match=r"is not an image collection"):
            LocalExportTransport().export(
                collection_id=collection_id,
                request=SampleQueryRequest(),
                limit=None,
                task=ExportTask(
                    export_format=ExportFormat.OBJECT_DETECTION_COCO,
                    output_path=tmp_path / "coco.json",
                    annotation_collection_id=None,
                ),
            )

    def test_export__collection_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(NotFoundError, match=r"does not exist"):
            LocalExportTransport().export(
                collection_id=uuid4(),
                request=SampleQueryRequest(),
                limit=None,
                task=ExportTask(
                    export_format=ExportFormat.OBJECT_DETECTION_COCO,
                    output_path=tmp_path / "coco.json",
                    annotation_collection_id=None,
                ),
            )
