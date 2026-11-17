from __future__ import annotations

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
from lightly_studio.models.video import VideoTable
from tests.helpers_resolvers import create_annotation, create_annotation_label, create_collection
from tests.resolvers.video.helpers import VideoStub, create_video


class TestVideoEventQuery:
    @pytest.mark.parametrize(
        ("expression", "expected_names"),
        [
            (VideoEventQuery(), {"events.mp4"}),
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
        self, db_session: Session, expression: MatchExpression, expected_names: set[str]
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
        for video_name, class_name, source, annotation_type, start, end, confidence in [
            ("events", "run", "ground_truth", AnnotationType.CLASSIFICATION, 3, 8, None),
            ("events", "walk", "model", AnnotationType.CLASSIFICATION, 8, 10, 0.5),
            ("whole", "run", "ground_truth", AnnotationType.CLASSIFICATION, None, None, None),
            ("detection", "run", "ground_truth", AnnotationType.OBJECT_DETECTION, None, None, None),
        ]:
            create_annotation(
                session=db_session,
                collection_id=collection.collection_id,
                sample_id=videos[video_name].sample_id,
                annotation_label_id=labels[class_name].annotation_label_id,
                annotation_type=annotation_type,
                annotation_collection_name=source,
                annotation_data={
                    "start_time_s": start,
                    "end_time_s": end,
                    "confidence": confidence,
                },
            )
        query = select(VideoTable).join(VideoTable.sample).where(expression.get())
        assert {video.file_name for video in db_session.exec(query)} == expected_names
