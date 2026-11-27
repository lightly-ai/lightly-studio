from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pytest
from sqlmodel import col

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
from lightly_studio.core.dataset_query.field import Field
from lightly_studio.core.dataset_query.field_expression import OrdinalFieldExpression
from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.core.dataset_query.object_detection_query import (
    ObjectDetectionField,
    ObjectDetectionQuery,
)
from lightly_studio.core.dataset_query.order_by import (
    OrderByAnnotationEvaluationMetricField,
    OrderByEvaluationMetricField,
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
from lightly_studio.models.evaluation_annotation_metric import EvaluationAnnotationSide
from lightly_studio.models.query_expr import FieldRef
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sample_query import EvaluationMetricSortKey, SortKey
from lightly_studio.models.sort_direction import SortDirection

_DATE = datetime(2024, 1, 2, tzinfo=timezone.utc)

# Criteria on video frames, at the top level of frames or in a `VideoFrameQuery` on videos.
_FRAME_MATCHES = [
    VideoFrameSampleField.frame_number > 10,
    VideoFrameSampleField.frame_timestamp_pts <= 1000,
    VideoFrameSampleField.rotation_deg == 90,
    VideoFrameSampleField.frame_timestamp_s != 1.5,
    VideoFrameSampleField.tags.contains("cat"),
    VideoFrameSampleField.parent_video.file_name == "a.mp4",
    VideoFrameSampleField.parent_video.file_path_abs != "/a.mp4",
    VideoFrameSampleField.parent_video.width >= 1920,
    VideoFrameSampleField.parent_video.height < 1080,
    VideoFrameSampleField.parent_video.fps > 29.97,
    VideoFrameSampleField.parent_video.fps == 30,
    VideoFrameSampleField.parent_video.duration_s == 2.5,
    VideoFrameSampleField.parent_video.duration_s != 3,
    VideoFrameSampleField.parent_video.tags.contains("cat"),
    OR(VideoFrameSampleField.frame_number < 5, VideoFrameSampleField.parent_video.width > 1),
]


def test_to_query_expr() -> None:
    match = AND(
        ImageSampleField.width > 100,
        OR(ImageSampleField.file_name == "a.png", NOT(ImageSampleField.tags.contains("cat"))),
    )

    query_expr = query_expr_conversion.to_query_expr(
        match_expression=match, sample_type=SampleType.IMAGE
    )

    assert query_expr is not None
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
    ("match", "expr_type", "table", "name"),
    [
        (VideoFrameSampleField.frame_number > 10, "integer_expr", "video_frame", "frame_number"),
        (
            VideoFrameSampleField.frame_timestamp_pts <= 1000,
            "integer_expr",
            "video_frame",
            "frame_timestamp_pts",
        ),
        (VideoFrameSampleField.rotation_deg == 90, "integer_expr", "video_frame", "rotation_deg"),
        (
            VideoFrameSampleField.frame_timestamp_s != 1.5,
            "ordinal_float_expr",
            "video_frame",
            "frame_timestamp_s",
        ),
        (VideoFrameSampleField.tags.contains("cat"), "tags_contains_expr", "video_frame", "tags"),
        (
            VideoFrameSampleField.parent_video.file_name == "a.mp4",
            "string_expr",
            "parent_video",
            "file_name",
        ),
        (
            VideoFrameSampleField.parent_video.file_path_abs != "/a.mp4",
            "string_expr",
            "parent_video",
            "file_path_abs",
        ),
        (VideoFrameSampleField.parent_video.width >= 1920, "integer_expr", "parent_video", "width"),
        (
            VideoFrameSampleField.parent_video.height < 1080,
            "integer_expr",
            "parent_video",
            "height",
        ),
        (VideoFrameSampleField.parent_video.fps == 30, "ordinal_float_expr", "parent_video", "fps"),
        (
            VideoFrameSampleField.parent_video.duration_s == 2.5,
            "ordinal_float_expr",
            "parent_video",
            "duration_s",
        ),
        (
            VideoFrameSampleField.parent_video.tags.contains("cat"),
            "tags_contains_expr",
            "parent_video",
            "tags",
        ),
    ],
)
def test_to_query_expr__video_frame_fields(
    match: MatchExpression, expr_type: str, table: str, name: str
) -> None:
    query_expr = query_expr_conversion.to_query_expr(
        match_expression=match, sample_type=SampleType.VIDEO_FRAME
    )

    assert query_expr is not None
    match_expr = query_expr.model_dump(mode="json")["match_expr"]
    assert match_expr["type"] == expr_type
    assert match_expr["field"] == {"table": table, "name": name}


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
        *[(SampleType.VIDEO_FRAME, match) for match in _FRAME_MATCHES],
        *[(SampleType.VIDEO, VideoFrameQuery(match)) for match in _FRAME_MATCHES],
    ],
)
def test_to_query_expr__same_sql(sample_type: SampleType, match: MatchExpression) -> None:
    query_expr = query_expr_conversion.to_query_expr(
        match_expression=match, sample_type=sample_type
    )

    assert query_expr is not None
    translated = query_translation.to_match_expression(
        expr=query_expr.match_expr, sample_type=sample_type
    )

    assert _sql(match=translated) == _sql(match=match)


# SQL compiles an empty AND to true, so the test compares with the conversion of the match
# without the empty AND terms.
@pytest.mark.parametrize(
    ("match", "match_without_empty_and"),
    [
        (AND(ImageSampleField.width > 1, AND()), AND(ImageSampleField.width > 1)),
        (AND(AND(), ImageSampleField.width > 1, AND(AND())), AND(ImageSampleField.width > 1)),
        (ObjectDetectionQuery(AND()), ObjectDetectionQuery()),
        (
            ObjectDetectionQuery(AND(), ObjectDetectionField.x > 1),
            ObjectDetectionQuery(ObjectDetectionField.x > 1),
        ),
        (SampleEvaluationQuery("run", AND()), SampleEvaluationQuery("run")),
        (
            SampleEvaluationQuery("run", AND(EvaluationMetricField("miou") < 0.3, AND())),
            SampleEvaluationQuery("run", AND(EvaluationMetricField("miou") < 0.3)),
        ),
    ],
)
def test_to_query_expr__empty_and(
    match: MatchExpression, match_without_empty_and: MatchExpression
) -> None:
    query_expr = query_expr_conversion.to_query_expr(
        match_expression=match, sample_type=SampleType.IMAGE
    )

    assert query_expr == query_expr_conversion.to_query_expr(
        match_expression=match_without_empty_and, sample_type=SampleType.IMAGE
    )


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
        (SampleType.IMAGE, OR()),
        (SampleType.IMAGE, NOT(AND())),
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
        (SampleType.IMAGE, VideoFrameSampleField.parent_video.width > 1),
        (SampleType.IMAGE, VideoFrameSampleField.parent_video.tags.contains("cat")),
        (SampleType.VIDEO, VideoFrameSampleField.parent_video.file_name == "a.mp4"),
        (SampleType.VIDEO, VideoFrameSampleField.parent_video.duration_s == 2.5),
        (SampleType.VIDEO, VideoFrameSampleField.parent_video.tags.contains("cat")),
        (
            SampleType.VIDEO_FRAME,
            ObjectDetectionQuery(VideoFrameSampleField.parent_video.width > 1),
        ),
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
        OrderByMetadataField(field_name="weather"),
        OrderByEvaluationMetricField(evaluation_run_name="run", metric_name="miou").desc(),
    ]

    sort_keys = query_expr_conversion.to_sort_keys(order_by=order_by, sample_type=SampleType.IMAGE)

    assert sort_keys == [
        SortKey(field=FieldRef(table="image", name="width"), direction=SortDirection.desc),
        SortKey(field=FieldRef(table="metadata", name="weather"), direction=SortDirection.asc),
        EvaluationMetricSortKey(run_name="run", metric_name="miou", direction=SortDirection.desc),
    ]


@pytest.mark.parametrize(
    ("field", "name"),
    [
        (VideoFrameSampleField.frame_number, "frame_number"),
        (VideoFrameSampleField.frame_timestamp_s, "frame_timestamp_s"),
        (VideoFrameSampleField.frame_timestamp_pts, "frame_timestamp_pts"),
        (VideoFrameSampleField.rotation_deg, "rotation_deg"),
    ],
)
def test_to_sort_keys__video_frame_fields(field: Field, name: str) -> None:
    sort_keys = query_expr_conversion.to_sort_keys(
        order_by=[OrderByField(field)], sample_type=SampleType.VIDEO_FRAME
    )

    assert sort_keys == [
        SortKey(field=FieldRef(table="video_frame", name=name), direction=SortDirection.asc)
    ]


@pytest.mark.parametrize(
    "order_by",
    [
        OrderByField(VideoSampleField.fps),
        OrderByField(ClassificationField.confidence),
        OrderByAnnotationEvaluationMetricField(
            evaluation_run_id=uuid.uuid4(),
            metric_name="iou",
            side=EvaluationAnnotationSide.PREDICTION,
            annotation_id_column=col(SampleTable.sample_id),
        ),
    ],
)
def test_to_sort_keys__not_supported(order_by: OrderByExpression) -> None:
    with pytest.raises(UnsupportedQueryError):
        query_expr_conversion.to_sort_keys(order_by=[order_by], sample_type=SampleType.IMAGE)


def test_to_sort_keys__nullable_field() -> None:
    order_by = OrderByField(VideoSampleField.duration_s)
    with pytest.raises(UnsupportedQueryError):
        query_expr_conversion.to_sort_keys(order_by=[order_by], sample_type=SampleType.VIDEO)


@pytest.mark.parametrize("sample_type", [SampleType.VIDEO, SampleType.VIDEO_FRAME])
def test_to_sort_keys__evaluation_metric_of_non_image__raises(sample_type: SampleType) -> None:
    order_by = OrderByEvaluationMetricField(evaluation_run_name="run", metric_name="miou")

    with pytest.raises(UnsupportedQueryError, match="Evaluation metric sorts"):
        query_expr_conversion.to_sort_keys(order_by=[order_by], sample_type=sample_type)


@pytest.mark.parametrize(
    ("sample_type", "order_by", "table", "name", "direction"),
    [
        (SampleType.IMAGE, OrderByField(ImageSampleField.file_name), "image", "file_name", "asc"),
        (
            SampleType.IMAGE,
            OrderByField(ImageSampleField.file_path_abs).desc(),
            "image",
            "file_path_abs",
            "desc",
        ),
        (SampleType.IMAGE, OrderByField(ImageSampleField.created_at), "image", "created_at", "asc"),
        (SampleType.IMAGE, OrderByField(ImageSampleField.width).desc(), "image", "width", "desc"),
        (SampleType.IMAGE, OrderByField(ImageSampleField.height), "image", "height", "asc"),
        (
            SampleType.VIDEO,
            OrderByField(VideoSampleField.created_at).desc(),
            "video",
            "created_at",
            "desc",
        ),
        (SampleType.VIDEO, OrderByField(VideoSampleField.fps).desc(), "video", "fps", "desc"),
        (
            SampleType.IMAGE,
            OrderByMetadataField(field_name="weather").desc(),
            "metadata",
            "weather",
            "desc",
        ),
        (
            SampleType.VIDEO,
            OrderByMetadataField(field_name="odometry.acc[1]"),
            "metadata",
            "odometry.acc[1]",
            "asc",
        ),
    ],
)
def test_to_sort_keys__field(
    sample_type: SampleType, order_by: OrderByExpression, table: str, name: str, direction: str
) -> None:
    sort_keys = query_expr_conversion.to_sort_keys(order_by=[order_by], sample_type=sample_type)

    assert sort_keys == [
        SortKey(field=FieldRef(table=table, name=name), direction=SortDirection(direction))
    ]


def _sql(match: MatchExpression) -> str:
    return str(match.get().compile(compile_kwargs={"literal_binds": True}))
