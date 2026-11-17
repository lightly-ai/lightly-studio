import pytest
from sqlmodel import Session, select

from lightly_studio.core.dataset_query import (
    NOT,
    ClassificationQuery,
    VideoEventField,
    VideoEventQuery,
)
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import SampleType
from lightly_studio.models.query_expr import QueryExpr
from lightly_studio.models.video import VideoTable
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
)
from tests.resolvers.video.helpers import VideoStub, create_video

EVENT_QUERIES = {
    end_time_s: QueryExpr.model_validate(
        {
            "match_expr": {
                "type": "video_event_match_expr",
                "subexpr": {
                    "type": "and",
                    "children": [
                        {
                            "type": "string_expr",
                            "field": {"table": "event", "name": "class_name"},
                            "operator": "==",
                            "value": "run",
                        },
                        {
                            "type": "ordinal_float_expr",
                            "field": {"table": "event", "name": "end_time_s"},
                            "operator": ">",
                            "value": end_time_s,
                        },
                    ],
                },
            }
        }
    )
    for end_time_s in [7, 8]
}


class TestVideoEventQuery:
    @pytest.mark.parametrize(
        ("expression", "expected_names"),
        [
            (VideoEventQuery(), {"events.mp4"}),
            (EVENT_QUERIES[7], {"events.mp4"}),
            (EVENT_QUERIES[8], set()),
            (ClassificationQuery(), {"events.mp4", "whole.mp4"}),
            (VideoEventQuery(VideoEventField.start_time_s < 3), set()),
            (VideoEventQuery(VideoEventField.start_time_s <= 3), {"events.mp4"}),
            (VideoEventQuery(VideoEventField.end_time_s == 8), {"events.mp4"}),
            (VideoEventQuery(VideoEventField.end_time_s > 8), {"events.mp4"}),
            (VideoEventQuery(VideoEventField.end_time_s >= 10), {"events.mp4"}),
            (VideoEventQuery(VideoEventField.end_time_s != 8), {"events.mp4"}),
            (
                VideoEventQuery(
                    VideoEventField.class_name == "run", VideoEventField.confidence >= 0
                ),
                set(),
            ),
            (VideoEventQuery(VideoEventField.confidence > 0.9), set()),
            (
                VideoEventQuery(
                    VideoEventField.class_name == "run", VideoEventField.start_time_s < 5
                ),
                {"events.mp4"},
            ),
            (
                VideoEventQuery(
                    VideoEventField.class_name == "run", VideoEventField.end_time_s > 8
                ),
                set(),
            ),
            (
                VideoEventQuery(
                    VideoEventField.class_name == "run", VideoEventField.source == "model"
                ),
                set(),
            ),
            (
                VideoEventQuery(
                    VideoEventField.source == "model", VideoEventField.confidence == 0.5
                ),
                {"events.mp4"},
            ),
            (NOT(VideoEventQuery()), {"whole.mp4", "detection.mp4", "empty.mp4"}),
        ],
    )
    def test_get__event_correlation(
        self, db_session: Session, expression: MatchExpression | QueryExpr, expected_names: set[str]
    ) -> None:
        collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
        labels = {
            name: create_annotation_label(
                session=db_session, root_collection_id=collection.collection_id, label_name=name
            )
            for name in ["run", "walk"]
        }
        videos = {
            name: create_video(
                session=db_session,
                collection_id=collection.collection_id,
                video=VideoStub(path=f"/data/{name}.mp4"),
            )
            for name in ["events", "whole", "detection", "empty"]
        }
        create_annotations(
            session=db_session,
            collection_id=collection.collection_id,
            collection_name="ground_truth",
            annotations=[
                AnnotationDetails(
                    sample_id=videos["events"].sample_id,
                    annotation_label_id=labels["run"].annotation_label_id,
                    annotation_type=AnnotationType.CLASSIFICATION,
                    start_time_s=3,
                    end_time_s=8,
                    confidence=None,
                ),
                AnnotationDetails(
                    sample_id=videos["whole"].sample_id,
                    annotation_label_id=labels["run"].annotation_label_id,
                    annotation_type=AnnotationType.CLASSIFICATION,
                ),
                AnnotationDetails(
                    sample_id=videos["detection"].sample_id,
                    annotation_label_id=labels["run"].annotation_label_id,
                    annotation_type=AnnotationType.OBJECT_DETECTION,
                ),
            ],
        )
        create_annotations(
            session=db_session,
            collection_id=collection.collection_id,
            collection_name="model",
            annotations=[
                AnnotationDetails(
                    sample_id=videos["events"].sample_id,
                    annotation_label_id=labels["walk"].annotation_label_id,
                    annotation_type=AnnotationType.CLASSIFICATION,
                    start_time_s=8,
                    end_time_s=10,
                    confidence=0.5,
                ),
            ],
        )
        query = select(VideoTable).join(VideoTable.sample)
        if isinstance(expression, QueryExpr):
            query = VideoFilter(sample_filter=SampleFilter(query_expr=expression)).apply(
                query=query
            )
        else:
            query = query.where(expression.get())
        assert {video.file_name for video in db_session.exec(query)} == expected_names
