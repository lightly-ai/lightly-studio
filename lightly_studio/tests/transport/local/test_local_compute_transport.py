from __future__ import annotations

from uuid import uuid4

import pytest

from lightly_studio.database import db_manager
from lightly_studio.models.collection import SampleType
from lightly_studio.models.query_expr import (
    FieldRef,
    IntegerExpr,
    OrdinalComparisonOperator,
    QueryExpr,
)
from lightly_studio.models.sample_query import SampleQueryRequest
from lightly_studio.resolvers import image_resolver, tag_resolver
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.sampling.sampling_config import EmbeddingDiversityStrategy, SamplingConfig
from lightly_studio.transport.compute_transport import ComputeTransport
from lightly_studio.transport.local.local_compute_transport import LocalComputeTransport
from tests.helpers_resolvers import (
    ImageStub,
    create_collection,
    create_embedding_model,
    create_samples_with_embeddings,
)


@pytest.mark.usefixtures("patch_collection")
class TestLocalComputeTransport:
    def test_compute_similarity__unknown_tag(self) -> None:
        session = db_manager.persistent_session()
        collection_id = create_collection(session=session).collection_id
        transport: ComputeTransport = LocalComputeTransport()

        with pytest.raises(ValueError, match=r"Query tag not found"):
            transport.compute_similarity(
                collection_id=collection_id,
                query_tag_name="query",
                embedding_model_name=None,
                metadata_name=None,
            )

    def test_sampling(self) -> None:
        session = db_manager.persistent_session()
        collection_id = create_collection(session=session).collection_id
        embedding_model = create_embedding_model(
            session=session, collection_id=collection_id, set_as_default=True
        )
        images = create_samples_with_embeddings(
            session=session,
            collection_id=collection_id,
            embedding_model_id=embedding_model.embedding_model_id,
            images_and_embeddings=[
                (ImageStub(path="a.jpg", width=10), [1.0, 0.0]),
                (ImageStub(path="b.jpg", width=20), [0.0, 1.0]),
            ],
        )
        narrow = IntegerExpr(
            field=FieldRef(table="image", name="width"),
            operator=OrdinalComparisonOperator.LT,
            value=15,
        )
        transport: ComputeTransport = LocalComputeTransport()

        transport.sampling(
            config=SamplingConfig(
                collection_id=collection_id,
                n_samples_to_select=1,
                sampling_result_tag_name="selected",
                strategies=[EmbeddingDiversityStrategy()],
            ),
            request=SampleQueryRequest(query_expr=QueryExpr(match_expr=narrow)),
            limit=None,
        )

        tag = tag_resolver.get_by_name(
            session=session, tag_name="selected", collection_id=collection_id
        )
        assert tag is not None
        selected_ids = image_resolver.get_sample_ids(
            session=session,
            collection_id=collection_id,
            filters=ImageFilter(sample_filter=SampleFilter(tag_ids=[tag.tag_id])),
        )
        assert selected_ids == {images[0].sample_id}

    def test_sampling__video_collection(self) -> None:
        session = db_manager.persistent_session()
        collection_id = create_collection(
            session=session, sample_type=SampleType.VIDEO
        ).collection_id
        transport: ComputeTransport = LocalComputeTransport()

        with pytest.raises(ValueError, match=r"is not an image collection"):
            transport.sampling(
                config=SamplingConfig(
                    collection_id=collection_id,
                    n_samples_to_select=1,
                    sampling_result_tag_name="selected",
                    strategies=[EmbeddingDiversityStrategy()],
                ),
                request=SampleQueryRequest(),
                limit=None,
            )

    def test_sampling__unknown_collection(self) -> None:
        collection_id = uuid4()
        transport: ComputeTransport = LocalComputeTransport()

        with pytest.raises(ValueError, match=r"is not an image collection"):
            transport.sampling(
                config=SamplingConfig(
                    collection_id=collection_id,
                    n_samples_to_select=1,
                    sampling_result_tag_name="selected",
                    strategies=[EmbeddingDiversityStrategy()],
                ),
                request=SampleQueryRequest(),
                limit=None,
            )
