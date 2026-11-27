from __future__ import annotations

from collections.abc import Callable
from uuid import UUID, uuid4

import pytest

from lightly_studio.database import db_manager
from lightly_studio.models.collection import SampleType
from lightly_studio.models.evaluation_confusion_matrix import NO_GROUND_TRUTH_ROW_LABEL
from lightly_studio.models.evaluation_run import EvaluationTaskType
from lightly_studio.models.evaluation_task import EvaluationTask, ObjectDetectionEvaluationConfig
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
from tests.api.routes.api.evaluation import helpers as evaluation_helpers
from tests.helpers_resolvers import (
    ImageStub,
    create_collection,
    create_embedding_model,
    create_samples_with_embeddings,
)

OBJECT_DETECTION_TASK = EvaluationTask(
    task_type=EvaluationTaskType.OBJECT_DETECTION,
    name="run",
    gt_annotation_source="gt",
    pred_annotation_source="pred",
    config=ObjectDetectionEvaluationConfig(),
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

    @pytest.mark.parametrize(
        ("query_expr", "sample_count"),
        [
            (None, 2),
            (
                QueryExpr(
                    match_expr=IntegerExpr(
                        field=FieldRef(table="image", name="width"),
                        operator=OrdinalComparisonOperator.LT,
                        value=15,
                    )
                ),
                1,
            ),
        ],
    )
    def test_evaluate(self, query_expr: QueryExpr | None, sample_count: int) -> None:
        collection = evaluation_helpers.create_dataset_with_annotations(
            db_session=db_manager.persistent_session(), image_widths=(10, 20)
        )
        transport: ComputeTransport = LocalComputeTransport()

        result = transport.evaluate(
            collection_id=collection.collection_id,
            query_expr=query_expr,
            task=OBJECT_DETECTION_TASK,
        )

        assert result.sample_count == sample_count
        assert result.gt_annotation_count == sample_count

    def test_evaluate__empty_name(self) -> None:
        collection = evaluation_helpers.create_dataset_with_annotations(
            db_session=db_manager.persistent_session()
        )
        transport: ComputeTransport = LocalComputeTransport()

        transport.evaluate(
            collection_id=collection.collection_id,
            query_expr=None,
            task=OBJECT_DETECTION_TASK.model_copy(update={"name": ""}),
        )

        runs = transport.list_evaluation_runs(collection_id=collection.collection_id)
        assert [run.name for run in runs] == [""]

    def test_evaluate__unknown_collection(self) -> None:
        transport: ComputeTransport = LocalComputeTransport()

        with pytest.raises(ValueError, match=r"not found"):
            transport.evaluate(collection_id=uuid4(), query_expr=None, task=OBJECT_DETECTION_TASK)

    def test_evaluate__video_collection(self) -> None:
        session = db_manager.persistent_session()
        collection_id = create_collection(
            session=session, sample_type=SampleType.VIDEO
        ).collection_id
        transport: ComputeTransport = LocalComputeTransport()

        with pytest.raises(ValueError, match=r"only be triggered on image collections"):
            transport.evaluate(
                collection_id=collection_id, query_expr=None, task=OBJECT_DETECTION_TASK
            )

    def test_list_evaluation_runs(self) -> None:
        collection_id, run_id = _create_evaluation_run(image_widths=(10,), label_name="dog")
        transport: ComputeTransport = LocalComputeTransport()

        runs = transport.list_evaluation_runs(collection_id=collection_id)

        assert [(run.id, run.name) for run in runs] == [(run_id, "run")]

    def test_get_evaluation_confusion_matrix(self) -> None:
        collection_id, run_id = _create_evaluation_run(image_widths=(10, 20), label_name="dog")
        transport: ComputeTransport = LocalComputeTransport()

        matrix = transport.get_evaluation_confusion_matrix(
            collection_id=collection_id, run_id=run_id
        )

        assert matrix.row_labels == ["dog", NO_GROUND_TRUTH_ROW_LABEL]
        assert matrix.counts == [[2, 0], [0, 0]]

    def test_get_evaluation_metrics(self) -> None:
        collection_id, run_id = _create_evaluation_run(image_widths=(10,), label_name="dog")
        transport: ComputeTransport = LocalComputeTransport()

        metrics = transport.get_evaluation_metrics(collection_id=collection_id, run_id=run_id)

        assert metrics.precision == 1.0
        assert metrics.recall == 1.0

    @pytest.mark.parametrize(
        "read_run",
        [
            LocalComputeTransport.get_evaluation_confusion_matrix,
            LocalComputeTransport.get_evaluation_metrics,
        ],
    )
    def test_get_evaluation__run_of_other_dataset(self, read_run: Callable[..., object]) -> None:
        _, run_id = _create_evaluation_run(image_widths=(10,), label_name="dog")
        other_collection_id = create_collection(
            session=db_manager.persistent_session()
        ).collection_id

        with pytest.raises(ValueError, match=r"not found in this dataset"):
            read_run(LocalComputeTransport(), collection_id=other_collection_id, run_id=run_id)


def _create_evaluation_run(image_widths: tuple[int, ...], label_name: str) -> tuple[UUID, UUID]:
    """Create an object detection run. The GT and the prediction of each image have the same box."""
    collection = evaluation_helpers.create_dataset_with_annotations(
        db_session=db_manager.persistent_session(), image_widths=image_widths, label_name=label_name
    )
    result = LocalComputeTransport().evaluate(
        collection_id=collection.collection_id, query_expr=None, task=OBJECT_DETECTION_TASK
    )
    return collection.collection_id, result.evaluation_run_id
