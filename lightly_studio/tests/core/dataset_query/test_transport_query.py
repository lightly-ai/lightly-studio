from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from pytest_mock import MockerFixture

from lightly_studio.core.dataset_query import transport_query
from lightly_studio.core.dataset_query.boolean_expression import AND
from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.order_by import (
    OrderByEvaluationMetricField,
    OrderByExpression,
    OrderByField,
    OrderByMetadataField,
)
from lightly_studio.core.dataset_query.query_expr_conversion import UnsupportedQueryError
from lightly_studio.core.dataset_query.video_frame_sample_field import VideoFrameSampleField
from lightly_studio.core.image.record_image_sample import RecordImageSample
from lightly_studio.database import db_manager
from lightly_studio.dataset import env
from lightly_studio.models.collection import SampleType
from lightly_studio.models.query_expr import (
    FieldRef,
    IntegerExpr,
    OrdinalComparisonOperator,
    QueryExpr,
)
from lightly_studio.models.sample_query import (
    EvaluationMetricSortKey,
    SampleQueryRequest,
    SortKey,
)
from lightly_studio.models.sort_direction import SortDirection
from lightly_studio.resolvers import metadata_resolver
from lightly_studio.transport import active_transport
from lightly_studio.transport.local.local_compute_transport import LocalComputeTransport
from tests.helpers_resolvers import (
    ImageStub,
    create_collection,
    create_embedding_model,
    create_image,
    create_samples_with_embeddings,
)


@pytest.fixture
def _transport_queries(mocker: MockerFixture) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_TRANSPORT_QUERIES", True)


def test_build_request__flag_off(mocker: MockerFixture) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_TRANSPORT_QUERIES", False)

    request = transport_query.build_request(
        sample_type=SampleType.IMAGE,
        match_expression=None,
        order_by=[],
        filters_sample_ids=False,
        offset=0,
    )

    assert request is None


@pytest.mark.parametrize("match", [AND(), AND(AND())])
@pytest.mark.usefixtures("_transport_queries")
def test_build_request__empty_and(match: AND) -> None:
    request = transport_query.build_request(
        sample_type=SampleType.IMAGE,
        match_expression=match,
        order_by=[],
        filters_sample_ids=False,
        offset=0,
    )

    assert request is not None
    assert request.query_expr is None


@pytest.mark.parametrize(
    ("order_by", "sort_key"),
    [
        (
            OrderByMetadataField(field_name="weather").desc(),
            SortKey(field=FieldRef(table="metadata", name="weather"), direction=SortDirection.desc),
        ),
        (
            OrderByEvaluationMetricField(evaluation_run_name="run", metric_name="miou"),
            EvaluationMetricSortKey(
                run_name="run", metric_name="miou", direction=SortDirection.asc
            ),
        ),
    ],
)
@pytest.mark.usefixtures("_transport_queries")
def test_build_request__offset_paging_sort(
    mocker: MockerFixture,
    order_by: OrderByExpression,
    sort_key: SortKey | EvaluationMetricSortKey,
) -> None:
    def build() -> SampleQueryRequest | None:
        return transport_query.build_request(
            sample_type=SampleType.IMAGE,
            match_expression=None,
            order_by=[order_by],
            filters_sample_ids=False,
            offset=0,
        )

    assert build() is None
    mocker.patch.object(active_transport, "is_remote", return_value=True)
    request = build()
    assert request is not None
    assert request.sort == [sort_key]


@pytest.mark.usefixtures("_transport_queries")
def test_build_request__not_supported(mocker: MockerFixture) -> None:
    def build() -> object:
        return transport_query.build_request(
            sample_type=SampleType.VIDEO,
            match_expression=None,
            order_by=[],
            filters_sample_ids=False,
            offset=0,
        )

    assert build() is None
    mocker.patch.object(active_transport, "is_remote", return_value=True)
    with pytest.raises(UnsupportedQueryError):
        build()


def test_build_export_request(mocker: MockerFixture) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_TRANSPORT_QUERIES", False)

    request = transport_query.build_export_request(
        sample_type=SampleType.IMAGE,
        match_expression=ImageSampleField.width > 10,
        order_by=[OrderByField(ImageSampleField.width).desc()],
        filters_sample_ids=False,
        offset=2,
    )

    assert request == SampleQueryRequest(
        query_expr=QueryExpr(
            match_expr=IntegerExpr(
                field=FieldRef(table="image", name="width"),
                operator=OrdinalComparisonOperator.GT,
                value=10,
            )
        ),
        sort=[SortKey(field=FieldRef(table="image", name="width"), direction=SortDirection.desc)],
        offset=2,
    )


@pytest.mark.parametrize(
    "unsupported",
    [
        {"filters_sample_ids": True},
        {"sample_type": SampleType.VIDEO},
        {"match_expression": VideoFrameSampleField.parent_video.width > 1},
        {"order_by": [OrderByField(VideoFrameSampleField.frame_number)]},
    ],
)
def test_build_export_request__not_supported(
    mocker: MockerFixture, unsupported: dict[str, Any]
) -> None:
    def build() -> object:
        supported: dict[str, Any] = {
            "sample_type": SampleType.IMAGE,
            "match_expression": None,
            "order_by": [],
            "filters_sample_ids": False,
            "offset": 0,
        }
        return transport_query.build_export_request(**{**supported, **unsupported})

    assert build() is None
    mocker.patch.object(active_transport, "is_remote", return_value=True)
    with pytest.raises(UnsupportedQueryError):
        build()


@pytest.mark.usefixtures("patch_collection", "_transport_queries")
def test_dataset_query__through_transport(mocker: MockerFixture) -> None:
    mocker.patch.object(transport_query, "DEFAULT_PAGE_SIZE", 1)
    session = db_manager.persistent_session()
    collection = create_collection(session=session)
    for path, width in [("/a.png", 10), ("/b.png", 20), ("/c.png", 30), ("/d.png", 40)]:
        create_image(
            session=session, collection_id=collection.collection_id, file_path_abs=path, width=width
        )
    query = DatasetQuery(dataset=collection, session=session)
    query.match(AND(ImageSampleField.width > 15)).order_by(
        OrderByField(ImageSampleField.width).desc()
    )[1:3]

    samples = query.to_list()
    query.add_tag("picked")

    assert all(isinstance(sample, RecordImageSample) for sample in samples)
    assert [sample.file_name for sample in samples] == ["c.png", "b.png"]
    assert [sample.tags for sample in query] == [{"picked"}, {"picked"}]


@pytest.mark.usefixtures("patch_collection")
@pytest.mark.parametrize("connect_transport", ["remote"], indirect=True)
def test_dataset_query__metadata_sort_through_transport(
    mocker: MockerFixture, connect_transport: Callable[[], None]
) -> None:
    mocker.patch.object(transport_query, "DEFAULT_PAGE_SIZE", 2)
    session = db_manager.persistent_session()
    collection = create_collection(session=session)
    images = [
        create_image(session=session, collection_id=collection.collection_id, file_path_abs=path)
        for path in ["/a.png", "/b.png", "/c.png", "/d.png", "/e.png"]
    ]
    metadata_resolver.bulk_update_metadata(
        session=session,
        sample_metadata=[
            (images[0].sample_id, {"score": 3}),
            (images[1].sample_id, {"score": 10}),
            (images[2].sample_id, {"score": 3}),
        ],
    )
    query = DatasetQuery(dataset=collection, session=session).order_by(
        OrderByMetadataField(field_name="score").desc()
    )
    sql_file_names = [sample.file_name for sample in query]
    connect_transport()

    samples = query.to_list()

    assert all(isinstance(sample, RecordImageSample) for sample in samples)
    assert [sample.file_name for sample in samples] == sql_file_names


@pytest.mark.usefixtures("patch_collection")
def test_dataset_query__sampling_through_transport(mocker: MockerFixture) -> None:
    session = db_manager.persistent_session()
    collection = create_collection(session=session)
    embedding_model = create_embedding_model(
        session=session, collection_id=collection.collection_id, set_as_default=True
    )
    create_samples_with_embeddings(
        session=session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
        images_and_embeddings=[
            (ImageStub(path="d.png", width=20), [0.4, 0.0]),
            (ImageStub(path="c.png", width=30), [1.0, 0.0]),
            (ImageStub(path="b.png", width=40), [0.0, 0.0]),
            (ImageStub(path="e.png", width=10), [0.0, 1.5]),
            (ImageStub(path="a.png", width=50), [0.0, 1.0]),
        ],
    )
    query = DatasetQuery(dataset=collection, session=session)
    query.order_by(OrderByField(ImageSampleField.width).desc())[1:4]
    mocker.patch.object(env, "LIGHTLY_STUDIO_TRANSPORT_QUERIES", False)
    query.sampling().diverse(n_samples_to_select=2, sampling_result_tag_name="sql")
    mocker.patch.object(env, "LIGHTLY_STUDIO_TRANSPORT_QUERIES", True)
    transport_sampling = mocker.spy(LocalComputeTransport, "sampling")

    query.sampling().diverse(n_samples_to_select=2, sampling_result_tag_name="transport")

    def tagged_file_names(tag_name: str) -> set[str]:
        tagged = DatasetQuery(dataset=collection, session=session)
        tagged.match(ImageSampleField.tags.contains(tag_name))
        return {sample.file_name for sample in tagged}

    assert tagged_file_names("sql") == tagged_file_names("transport") == {"b.png", "c.png"}
    transport_sampling.assert_called_once()
