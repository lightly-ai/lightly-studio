from collections.abc import Callable

import pytest
from sqlalchemy import func
from sqlmodel import Session, select

from lightly_studio.core.dataset_query import (
    AND,
    NOT,
    OR,
    ClassificationQuery,
    EvaluationMetricField,
    ObjectDetectionField,
    ObjectDetectionQuery,
    SampleEvaluationQuery,
    VideoEventQuery,
    VideoFrameQuery,
    VideoFrameSampleField,
)
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import SampleType
from lightly_studio.models.query_expr import (
    AndExpr,
    ClassificationMatchExpr,
    EqualityComparisonOperator,
    FieldRef,
    ObjectDetectionMatchExpr,
    OrdinalComparisonOperator,
    OrdinalFloatExpr,
    PolygonMatchExpr,
    QueryExpr,
    SegmentationMaskMatchExpr,
    StringExpr,
    VideoFrameMatchExpr,
)
from lightly_studio.models.video import VideoTable
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
)
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames

PERSON = ObjectDetectionQuery(ObjectDetectionField.class_name == "person")
CAR = ObjectDetectionQuery(ObjectDetectionField.class_name == "car")


API_ANNOTATIONS = {
    name: ObjectDetectionMatchExpr(
        subexpr=StringExpr(
            field=FieldRef(table="object_detection", name="class_name"),
            operator=EqualityComparisonOperator.EQ,
            value=name,
        )
    )
    for name in ["person", "car"]
}


class TestVideoFrameQuery:
    @pytest.mark.parametrize(
        "nested_query", [VideoFrameQuery(), VideoEventQuery()], ids=["frame", "event"]
    )
    @pytest.mark.parametrize(
        "wrap_criterion",
        [
            pytest.param(lambda query: SampleEvaluationQuery("run", query), id="direct"),
            pytest.param(
                lambda query: SampleEvaluationQuery(
                    "run", EvaluationMetricField(metric_name="score") > 0.5, query
                ),
                id="multiple-criteria",
            ),
            pytest.param(
                lambda query: SampleEvaluationQuery("run", AND(PERSON, OR(CAR, NOT(query)))),
                id="boolean",
            ),
            pytest.param(lambda query: NOT(SampleEvaluationQuery("run", query)), id="negated"),
            pytest.param(
                lambda query: ClassificationQuery(SampleEvaluationQuery("run", query)),
                id="classification",
            ),
            pytest.param(
                lambda query: SampleEvaluationQuery("run", ObjectDetectionQuery(query)),
                id="object-detection",
            ),
            pytest.param(
                lambda query: SampleEvaluationQuery("run", SampleEvaluationQuery("other", query)),
                id="nested-evaluation",
            ),
        ],
    )
    def test_init__reject_nested_evaluation_queries(
        self,
        nested_query: MatchExpression,
        wrap_criterion: Callable[[MatchExpression], MatchExpression],
    ) -> None:
        criterion = wrap_criterion(nested_query)
        with pytest.raises(ValueError, match="cannot contain frame or event queries"):
            VideoFrameQuery(criterion)

    @pytest.mark.parametrize(
        "criterion",
        [
            SampleEvaluationQuery(run_name="run"),
            SampleEvaluationQuery("run", EvaluationMetricField(metric_name="score") > 0.5),
            SampleEvaluationQuery(
                "run",
                EvaluationMetricField(metric_name="score") > 0.5,
                EvaluationMetricField(metric_name="recall") > 0.8,
            ),
            SampleEvaluationQuery(
                "run",
                AND(
                    EvaluationMetricField(metric_name="score") > 0.5,
                    NOT(EvaluationMetricField(metric_name="recall") < 0.8),
                ),
            ),
        ],
    )
    def test_init__accept_evaluation_criteria(self, criterion: MatchExpression) -> None:
        VideoFrameQuery(criterion).get()

    @pytest.mark.parametrize(
        ("expression", "expected_names"),
        [
            (
                QueryExpr(match_expr=VideoFrameMatchExpr(subexpr=ObjectDetectionMatchExpr())),
                {"together.mp4", "apart.mp4"},
            ),
            (VideoFrameQuery(PERSON, CAR), {"together.mp4"}),
            (
                QueryExpr(
                    match_expr=VideoFrameMatchExpr(
                        subexpr=AndExpr(children=list(API_ANNOTATIONS.values()))
                    )
                ),
                {"together.mp4"},
            ),
            (
                QueryExpr(
                    match_expr=AndExpr(
                        children=[
                            VideoFrameMatchExpr(subexpr=expr) for expr in API_ANNOTATIONS.values()
                        ]
                    )
                ),
                {"together.mp4", "apart.mp4"},
            ),
            (
                QueryExpr(
                    match_expr=VideoFrameMatchExpr(
                        subexpr=AndExpr(
                            children=[
                                API_ANNOTATIONS["car"],
                                OrdinalFloatExpr(
                                    field=FieldRef(table="video_frame", name="frame_timestamp_s"),
                                    operator=OrdinalComparisonOperator.GTE,
                                    value=1,
                                ),
                            ]
                        )
                    )
                ),
                {"apart.mp4"},
            ),
            (VideoFrameQuery(AND(PERSON, CAR)), {"together.mp4"}),
            (AND(VideoFrameQuery(PERSON), VideoFrameQuery(CAR)), {"together.mp4", "apart.mp4"}),
            (VideoFrameQuery(OR(PERSON, CAR)), {"together.mp4", "apart.mp4"}),
            (VideoFrameQuery(NOT(PERSON)), {"together.mp4", "apart.mp4", "bare.mp4"}),
            (NOT(VideoFrameQuery(PERSON)), {"bare.mp4", "empty.mp4"}),
            (VideoFrameQuery(CAR, VideoFrameSampleField.frame_timestamp_s < 1), {"together.mp4"}),
            (VideoFrameQuery(CAR, VideoFrameSampleField.frame_timestamp_s >= 1), {"apart.mp4"}),
            (VideoFrameQuery(), {"together.mp4", "apart.mp4", "bare.mp4"}),
        ],
    )
    def test_get__frame_correlation(
        self, db_session: Session, expression: MatchExpression | QueryExpr, expected_names: set[str]
    ) -> None:
        collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
        labels = {
            name: create_annotation_label(
                session=db_session, root_collection_id=collection.collection_id, label_name=name
            )
            for name in ["person", "car"]
        }
        for name, duration, frame_annotations in [
            ("together.mp4", 2, [(0, "person"), (0, "car")]),
            ("apart.mp4", 2, [(0, "person"), (1, "car")]),
            ("bare.mp4", 2, []),
            ("empty.mp4", 0, []),
        ]:
            video = create_video_with_frames(
                session=db_session,
                collection_id=collection.collection_id,
                video=VideoStub(path=f"/data/{name}", duration_s=duration, fps=1),
            )
            create_annotations(
                session=db_session,
                collection_id=video.video_frames_collection_id,
                annotations=[
                    AnnotationDetails(
                        sample_id=video.frame_sample_ids[frame_index],
                        annotation_label_id=labels[class_name].annotation_label_id,
                        annotation_type=AnnotationType.OBJECT_DETECTION,
                    )
                    for frame_index, class_name in frame_annotations
                ],
            )
        query = select(VideoTable).join(VideoTable.sample)
        if isinstance(expression, QueryExpr):
            restored = QueryExpr.model_validate_json(expression.model_dump_json())
            query = VideoFilter(sample_filter=SampleFilter(query_expr=restored)).apply(query=query)
            assert db_session.exec(select(func.count()).select_from(query.subquery())).one() == len(
                expected_names
            )
            for offset, name in enumerate(sorted(expected_names)):
                page = query.order_by(VideoTable.file_name).offset(offset).limit(1)
                assert [video.file_name for video in db_session.exec(page)] == [name]
        else:
            query = query.where(expression.get())
        assert {video.file_name for video in db_session.exec(query)} == expected_names

    @pytest.mark.parametrize(
        ("annotation_type", "expression"),
        [
            (
                AnnotationType.CLASSIFICATION,
                ClassificationMatchExpr(
                    subexpr=StringExpr(
                        field=FieldRef(table="classification", name="source"),
                        operator=EqualityComparisonOperator.EQ,
                        value="model",
                    )
                ),
            ),
            (
                AnnotationType.OBJECT_DETECTION,
                ObjectDetectionMatchExpr(
                    subexpr=StringExpr(
                        field=FieldRef(table="object_detection", name="source"),
                        operator=EqualityComparisonOperator.EQ,
                        value="model",
                    )
                ),
            ),
            (
                AnnotationType.SEGMENTATION_MASK,
                SegmentationMaskMatchExpr(
                    subexpr=StringExpr(
                        field=FieldRef(table="segmentation_mask", name="source"),
                        operator=EqualityComparisonOperator.EQ,
                        value="model",
                    )
                ),
            ),
            (
                AnnotationType.POLYGON,
                PolygonMatchExpr(
                    subexpr=StringExpr(
                        field=FieldRef(table="polygon", name="source"),
                        operator=EqualityComparisonOperator.EQ,
                        value="model",
                    )
                ),
            ),
        ],
    )
    def test_get__annotation_types_and_sources(
        self,
        db_session: Session,
        annotation_type: AnnotationType,
        expression: (
            ClassificationMatchExpr
            | ObjectDetectionMatchExpr
            | SegmentationMaskMatchExpr
            | PolygonMatchExpr
        ),
    ) -> None:
        collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
        label = create_annotation_label(
            session=db_session, root_collection_id=collection.collection_id, label_name="person"
        )
        for source in ["model", "ground_truth"]:
            video = create_video_with_frames(
                session=db_session,
                collection_id=collection.collection_id,
                video=VideoStub(path=f"/data/{source}.mp4", duration_s=2, fps=1),
            )
            create_annotations(
                session=db_session,
                collection_id=video.video_frames_collection_id,
                collection_name=source,
                annotations=[
                    AnnotationDetails(
                        sample_id=sample_id,
                        annotation_label_id=label.annotation_label_id,
                        annotation_type=annotation_type,
                        segmentation_mask=[0, 400],
                        polygons=[[(0.0, 0.0), (20.0, 0.0), (20.0, 20.0)]],
                    )
                    for sample_id in video.frame_sample_ids
                ],
            )
        query = select(VideoTable).join(VideoTable.sample)
        query_expr = QueryExpr(match_expr=VideoFrameMatchExpr(subexpr=expression))
        query = VideoFilter(sample_filter=SampleFilter(query_expr=query_expr)).apply(query=query)
        assert [video.file_name for video in db_session.exec(query)] == ["model.mp4"]
