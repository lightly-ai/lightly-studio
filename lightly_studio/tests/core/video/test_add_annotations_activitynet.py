"""Tests for ActivityNet annotation import."""

from __future__ import annotations

import json
from pathlib import Path

from sqlmodel import Session

from lightly_studio.core.video import add_annotations
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import annotation_resolver, video_resolver
from tests.helpers_resolvers import create_collection
from tests.resolvers.video.helpers import VideoStub, create_video


def test_add_annotations_from_activitynet__imports_events(
    db_session: Session, tmp_path: Path
) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video = create_video(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="/data/videos/v_action1.mp4", duration_s=30.0),
    )

    annotations_json = tmp_path / "activitynet.json"
    annotations_json.write_text(
        json.dumps(
            {
                "database": {
                    "v_action1": {
                        "annotations": [
                            {"label": "Running", "segment": [1.0, 5.5]},
                            {"label": "Jumping", "segment": [6.0, 12.0], "score": 0.8},
                        ]
                    },
                    "v_missing": {"annotations": [{"label": "Missing", "segment": [0.0, 1.0]}]},
                }
            }
        ),
        encoding="utf-8",
    )

    missing = add_annotations.add_annotations_from_activitynet(
        session=db_session,
        root_collection_id=collection.collection_id,
        annotations_json=annotations_json,
        collection_name="ground_truth",
    )

    assert missing == ["v_missing"]

    annotations = annotation_resolver.get_all_by_parent_sample_ids(
        session=db_session,
        parent_sample_ids=[video.sample_id],
    )
    assert len(annotations) == 2
    assert all(
        annotation.annotation_type == AnnotationType.CLASSIFICATION for annotation in annotations
    )
    assert all(annotation.parent_sample_id == video.sample_id for annotation in annotations)
    assert {
        annotation.temporal_span_details.start_time_s
        for annotation in annotations
        if annotation.temporal_span_details is not None
    } == {1.0, 6.0}
    assert {
        annotation.temporal_span_details.end_time_s
        for annotation in annotations
        if annotation.temporal_span_details is not None
    } == {5.5, 12.0}

    labels = {
        annotation.annotation_label.annotation_label_name
        for annotation in annotations
        if annotation.annotation_label is not None
    }
    assert labels == {"Running", "Jumping"}

    loaded_video = video_resolver.get_by_id(session=db_session, sample_id=video.sample_id)
    assert loaded_video is not None
