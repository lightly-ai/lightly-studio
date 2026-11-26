from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np
import pytest

from lightly_studio.core.dataset_query import query_expr_conversion, query_translation
from lightly_studio.core.dataset_query.annotation_evaluation_metric_expression import (
    AnnotationEvaluationMetricField,
)
from lightly_studio.core.dataset_query.annotation_evaluation_query import AnnotationMetricQuery
from lightly_studio.core.dataset_query.boolean_expression import AND, NOT, OR
from lightly_studio.core.dataset_query.classification_query import (
    ClassificationField,
    ClassificationQuery,
)
from lightly_studio.core.dataset_query.evaluation_metric_expression import EvaluationMetricField
from lightly_studio.core.dataset_query.field_expression import OrdinalFieldExpression
from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.core.dataset_query.object_detection_query import (
    ObjectDetectionField,
    ObjectDetectionQuery,
)
from lightly_studio.core.dataset_query.order_by import (
    OrderByExpression,
    OrderByField,
    OrderByMetadataField,
)
from lightly_studio.core.dataset_query.polygon_query import PolygonField, PolygonQuery
from lightly_studio.core.dataset_query.query_expr_conversion import UnsupportedQueryError
from lightly_studio.core.dataset_query.sample_evaluation_query import SampleEvaluationQuery
from lightly_studio.core.dataset_query.segmentation_mask_query import (
    SegmentationMaskField,
    SegmentationMaskQuery,
)
from lightly_studio.core.dataset_query.video_event_query import VideoEventField, VideoEventQuery
from lightly_studio.core.dataset_query.video_frame_query import VideoFrameQuery
from lightly_studio.core.dataset_query.video_frame_sample_field import VideoFrameSampleField
from lightly_studio.core.dataset_query.video_sample_field import VideoSampleField
from lightly_studio.models.collection import SampleType
from lightly_studio.models.query_expr import FieldRef
from lightly_studio.models.sample_query import SortKey
from lightly_studio.models.sort_direction import SortDirection

_DATE = datetime(2024, 1, 2, tzinfo=timezone.utc)


def test_to_query_expr() -> None:
    match = AND(
        ImageSampleField.width > 100,
        OR(ImageSampleField.file_name == "a.png", NOT(ImageSampleField.tags.contains("cat"))),
    )

    query_expr = query_expr_conversion.to_query_expr(
        match_expression=match, sample_type=SampleType.IMAGE
    )

    assert query_expr.model_dump(mode="json") == {
        "match_expr": {
            "type": "and",
            "children": [
                {
                    "type": "integer_expr",
                    "field": {"table": "image", "name": "width"},
                    "operator": ">",
                    "value": 100,
                },
                {
                    "type": "or",
                    "children": [
                        {
                            "type": "string_expr",
                            "field": {"table": "image", "name": "file_name"},
                            "operator": "==",
                            "value": "a.png",
                        },
                        {
                            "type": "not",
                            "child": {
                                "type": "tags_contains_expr",
                                "field": {"table": "image", "name": "tags"},
                                "tag_name": "cat",
                            },
                        },
                    ],
                },
            ],
        }
    }


@pytest.mark.parametrize(
    ("sample_type", "match"),
    [
        (SampleType.IMAGE, ImageSampleField.file_name == "a.png"),
        (SampleType.IMAGE, ImageSampleField.file_path_abs != "/a.png"),
        (SampleType.IMAGE, ImageSampleField.width > 100),
        (SampleType.IMAGE, ImageSampleField.height <= 100),
        (SampleType.IMAGE, ImageSampleField.created_at >= _DATE),
        (SampleType.IMAGE, ImageSampleField.tags.contains("cat")),
        (SampleType.IMAGE, ImageSampleField.metadata["weather"] == "sunny"),
        (SampleType.IMAGE, ImageSampleField.metadata["odometry.acc[1]"] < 1.5),
        (SampleType.IMAGE, ImageSampleField.metadata["night"] != True),  # noqa: E712
        (SampleType.VIDEO, VideoSampleField.file_name != "a.mp4"),
        (SampleType.VIDEO, VideoSampleField.file_path_abs == "/a.mp4"),
        (SampleType.VIDEO, VideoSampleField.width < 100),
        (SampleType.VIDEO, VideoSampleField.height == 100),
        (SampleType.VIDEO, VideoSampleField.fps > 29.97),
        (SampleType.VIDEO, VideoSampleField.fps == 30),
        (SampleType.VIDEO, VideoSampleField.duration_s <= 2.5),
        (SampleType.VIDEO, VideoSampleField.duration_s != 3),
        (SampleType.VIDEO, VideoSampleField.created_at > _DATE),
        (SampleType.VIDEO, VideoSampleField.tags.contains("cat")),
        (SampleType.VIDEO_FRAME, VideoFrameSampleField.tags.contains("cat")),
        (SampleType.VIDEO, VideoSampleField.metadata["weather"] == "sunny"),
        (SampleType.VIDEO, OR(AND(VideoSampleField.fps < 10), NOT(VideoSampleField.width > 1))),
        (SampleType.IMAGE, ClassificationQuery()),
        (SampleType.IMAGE, ClassificationQuery(ClassificationField.class_name == "cat")),
        (SampleType.IMAGE, ClassificationQuery(ClassificationField.source != "model")),
        (SampleType.IMAGE, ClassificationQuery(ClassificationField.confidence > 0.5)),
        (
            SampleType.IMAGE,
            ObjectDetectionQuery(
                ObjectDetectionField.class_name != "cat", ObjectDetectionField.x >= 10
            ),
        ),
        (SampleType.IMAGE, ObjectDetectionQuery(ObjectDetectionField.source == "model")),
        (SampleType.IMAGE, ObjectDetectionQuery(ObjectDetectionField.confidence <= 0.5)),
        (SampleType.IMAGE, SegmentationMaskQuery()),
        (SampleType.IMAGE, SegmentationMaskQuery(SegmentationMaskField.y < 10)),
        (SampleType.IMAGE, SegmentationMaskQuery(SegmentationMaskField.width > 10)),
        (SampleType.IMAGE, PolygonQuery(PolygonField.height == 10)),
        (
            SampleType.IMAGE,
            PolygonQuery(OR(PolygonField.class_name == "a", NOT(PolygonField.x < 1))),
        ),
        (SampleType.IMAGE, NOT(PolygonQuery(PolygonField.confidence != 0.5))),
        (SampleType.VIDEO, VideoEventQuery(VideoEventField.class_name == "run")),
        (SampleType.VIDEO, VideoEventQuery(VideoEventField.source == "model")),
        (
            SampleType.VIDEO,
            VideoEventQuery(VideoEventField.start_time_s >= 1, VideoEventField.end_time_s < 2.5),
        ),
        (SampleType.VIDEO, VideoEventQuery(VideoEventField.confidence > 0.5)),
        (SampleType.VIDEO, VideoFrameQuery(VideoFrameSampleField.frame_timestamp_s > 1.5)),
        (
            SampleType.VIDEO,
            VideoFrameQuery(
                ObjectDetectionQuery(ObjectDetectionField.width > 10),
                ClassificationQuery(ClassificationField.class_name == "cat"),
            ),
        ),
        (SampleType.IMAGE, SampleEvaluationQuery("run")),
        (
            SampleType.IMAGE,
            SampleEvaluationQuery(
                "run",
                EvaluationMetricField("miou") < 0.3,
                OR(EvaluationMetricField("f1") >= 1, NOT(EvaluationMetricField("p") != 0.5)),
                AND(EvaluationMetricField("r") == 2),
            ),
        ),
        (SampleType.IMAGE, AnnotationMetricQuery.confusion("run", "cat", "dog")),
        (
            SampleType.IMAGE,
            AnnotationMetricQuery.confusion(
                "run",
                "cat",
                "cat",
                AnnotationEvaluationMetricField("iou") > 0.3,
                AnnotationEvaluationMetricField("iou") <= 0.9,
            ),
        ),
        (SampleType.IMAGE, AnnotationMetricQuery.false_positive(run_name="run", prediction="dog")),
        (
            SampleType.VIDEO,
            NOT(AnnotationMetricQuery.false_negative(run_name="run", ground_truth="cat")),
        ),
    ],
)
def test_to_query_expr__same_sql(sample_type: SampleType, match: MatchExpression) -> None:
    query_expr = query_expr_conversion.to_query_expr(
        match_expression=match, sample_type=sample_type
    )

    translated = query_translation.to_match_expression(
        expr=query_expr.match_expr, sample_type=sample_type
    )

    assert _sql(match=translated) == _sql(match=match)


@pytest.mark.parametrize(
    ("sample_type", "match"),
    [
        (SampleType.IMAGE, ImageSampleField.width > 1.5),
        (
            SampleType.IMAGE,
            OrdinalFieldExpression[Any](field=ImageSampleField.created_at, operator=">", value=0),
        ),
        (SampleType.VIDEO, VideoSampleField.fps > float("inf")),
        (
            SampleType.VIDEO,
            OrdinalFieldExpression[Any](
                field=VideoSampleField.fps, operator=">", value=np.float32("inf")
            ),
        ),
        (SampleType.IMAGE, VideoSampleField.width > 100),
        (SampleType.VIDEO, ImageSampleField.width > 100),
        (SampleType.IMAGE, AND()),
        (SampleType.IMAGE, ClassificationField.class_name == "cat"),
        (SampleType.IMAGE, ClassificationQuery(ObjectDetectionField.x > 1)),
        (SampleType.IMAGE, ClassificationQuery(ImageSampleField.width > 1)),
        (SampleType.IMAGE, ClassificationQuery(VideoEventField.start_time_s > 1)),
        (SampleType.IMAGE, ClassificationField.source == "model"),
        (SampleType.IMAGE, PolygonQuery()),
        (SampleType.IMAGE, VideoFrameQuery(VideoFrameSampleField.frame_timestamp_s > 1)),
        (SampleType.VIDEO, VideoEventQuery()),
        (SampleType.VIDEO, VideoFrameSampleField.frame_timestamp_s > 1),
        (SampleType.VIDEO, VideoFrameSampleField.parent_video.width > 1),
        (SampleType.IMAGE, EvaluationMetricField("miou") < 0.3),
        (SampleType.IMAGE, AnnotationEvaluationMetricField("iou") > 0.3),
        (
            SampleType.IMAGE,
            SampleEvaluationQuery("run", AnnotationEvaluationMetricField("iou") > 1),
        ),
        (SampleType.IMAGE, SampleEvaluationQuery("run", AND())),
        (
            SampleType.IMAGE,
            AnnotationMetricQuery(
                match_kind="false_positive",
                run_name="run",
                gt_label_name=None,
                pred_label_name="dog",
                criteria=[AnnotationEvaluationMetricField("iou") > 0.3],
            ),
        ),
        (
            SampleType.IMAGE,
            AnnotationMetricQuery(
                match_kind="confusion",
                run_name="run",
                gt_label_name=None,
                pred_label_name="dog",
                criteria=[],
            ),
        ),
        (SampleType.IMAGE, ObjectDetectionQuery(SampleEvaluationQuery("run"))),
        (
            SampleType.VIDEO,
            VideoEventQuery(AnnotationMetricQuery.false_positive(run_name="run", prediction="dog")),
        ),
        (SampleType.VIDEO, VideoFrameQuery(SampleEvaluationQuery("run"))),
    ],
)
def test_to_query_expr__not_supported(sample_type: SampleType, match: MatchExpression) -> None:
    with pytest.raises(UnsupportedQueryError):
        query_expr_conversion.to_query_expr(match_expression=match, sample_type=sample_type)


@pytest.mark.parametrize(
    "criterion",
    [
        NOT(AnnotationEvaluationMetricField("iou") > 0.3),
        AND(AnnotationEvaluationMetricField("iou") > 0.3),
        EvaluationMetricField("miou") < 0.3,
    ],
)
def test_to_query_expr__confusion_criterion_not_supported(criterion: Any) -> None:
    match = AnnotationMetricQuery.confusion("run", "cat", "dog", criterion)

    with pytest.raises(UnsupportedQueryError):
        query_expr_conversion.to_query_expr(match_expression=match, sample_type=SampleType.IMAGE)


def test_to_sort_keys() -> None:
    order_by = [
        OrderByField(ImageSampleField.width).desc(),
        OrderByField(ImageSampleField.created_at),
    ]

    sort_keys = query_expr_conversion.to_sort_keys(order_by=order_by, sample_type=SampleType.IMAGE)

    assert sort_keys == [
        SortKey(field=FieldRef(table="image", name="width"), direction=SortDirection.desc),
        SortKey(field=FieldRef(table="image", name="created_at"), direction=SortDirection.asc),
    ]


@pytest.mark.parametrize(
    "order_by",
    [OrderByMetadataField(field_name="weather"), OrderByField(VideoSampleField.fps)],
)
def test_to_sort_keys__not_supported(order_by: OrderByExpression) -> None:
    with pytest.raises(UnsupportedQueryError):
        query_expr_conversion.to_sort_keys(order_by=[order_by], sample_type=SampleType.IMAGE)


def _sql(match: MatchExpression) -> str:
    return str(match.get().compile(compile_kwargs={"literal_binds": True}))
