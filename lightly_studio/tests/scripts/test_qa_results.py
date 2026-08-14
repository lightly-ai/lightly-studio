from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest
from pytest_mock import MockerFixture

from lightly_studio.core.video.video_dataset import VideoDataset
from lightly_studio.core.video.video_sample import VideoSample
from lightly_studio.models.caption import CaptionTable
from lightly_studio.resolvers import metadata_resolver
from scripts import qa_pull, qa_results


def test_build_result_records__includes_source_video_and_all_metadata(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    triplet = _local_triplet(tmp_path=tmp_path, stem="nested/clip")
    video = _video(mocker=mocker, video_path=triplet.video_path)
    dataset = _dataset(mocker=mocker, video=video)
    metadata = {
        qa_results.PIPELINE_COMPLETE_KEY: True,
        "automated_qa_status": "pass",
        "blur_score": 123.4,
    }
    caption = cast(
        CaptionTable,
        SimpleNamespace(
            sample_id=uuid4(),
            text="I pick up the shirt.",
            temporal_span_details=SimpleNamespace(start_time_s=1.5, end_time_s=3.0),
            metadata_dict=SimpleNamespace(
                data={"narration_label": "TASK", "narration_reason": "Describes an action."}
            ),
        ),
    )
    video.sample_table.captions = [caption]
    expire = mocker.patch.object(dataset.session, "expire")
    mocker.patch.object(
        metadata_resolver,
        "get_by_sample_id",
        return_value=SimpleNamespace(data=metadata),
    )

    records = qa_results.build_result_records(dataset=dataset, triplets=[triplet])

    _, object_name, record = records[0]
    assert object_name == "automated_qa_results/nested/clip_results.json"
    assert record["source"]["video_url"] == "gs://bucket/review/nested/clip.mp4"
    assert record["source"]["files"] == list(triplet.source_files)
    assert record["video"]["file_name"] == "clip.mp4"
    assert record["metadata"] == metadata
    assert record["narration_chunks"] == [
        {
            "sample_id": str(caption.sample_id),
            "text": "I pick up the shirt.",
            "start_time_s": 1.5,
            "end_time_s": 3.0,
            "metadata": {
                "narration_label": "TASK",
                "narration_reason": "Describes an action.",
            },
        }
    ]
    expire.assert_called_once_with(video.sample_table, ["captions"])


def test_build_result_records__rejects_incomplete_video(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    triplet = _local_triplet(tmp_path=tmp_path, stem="clip")
    video = _video(mocker=mocker, video_path=triplet.video_path)
    dataset = _dataset(mocker=mocker, video=video)
    mocker.patch.object(
        metadata_resolver,
        "get_by_sample_id",
        return_value=SimpleNamespace(data={qa_results.PIPELINE_COMPLETE_KEY: False}),
    )

    with pytest.raises(RuntimeError, match="incomplete QA result"):
        qa_results.build_result_records(dataset=dataset, triplets=[triplet])


def test_upload_result_records__writes_json_to_source_bucket(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    triplet = _local_triplet(tmp_path=tmp_path, stem="clip")
    client = mocker.MagicMock()
    record = {"metadata": {"automated_qa_status": "pass"}}
    mocker.patch.object(
        qa_results,
        "build_result_records",
        return_value=[(triplet, "automated_qa_results/clip_results.json", record)],
    )

    urls = qa_results.upload_result_records(
        client=client,
        dataset=mocker.MagicMock(),
        triplets=[triplet],
    )

    assert urls == ["gs://bucket/automated_qa_results/clip_results.json"]
    blob = client.bucket.return_value.blob.return_value
    payload = json.loads(blob.upload_from_string.call_args.args[0])
    assert payload == record
    blob.upload_from_string.assert_called_once_with(
        mocker.ANY,
        content_type="application/json",
    )


def test_filter_unpublished_triplets__lists_each_bucket_once(mocker: MockerFixture) -> None:
    published = _remote_triplet(bucket="first-bucket", stem="published")
    pending = _remote_triplet(bucket="first-bucket", stem="pending")
    other_bucket = _remote_triplet(bucket="second-bucket", stem="other")
    client = mocker.MagicMock()
    client.list_blobs.side_effect = [
        [SimpleNamespace(name="automated_qa_results/published_results.json")],
        [],
    ]

    result = qa_results.filter_unpublished_triplets(
        client=client,
        triplets=[published, pending, other_bucket],
    )

    assert result == [pending, other_bucket]
    assert client.list_blobs.call_args_list == [
        mocker.call("first-bucket", prefix="automated_qa_results/"),
        mocker.call("second-bucket", prefix="automated_qa_results/"),
    ]


def _dataset(mocker: MockerFixture, video: VideoSample) -> VideoDataset:
    dataset = mocker.MagicMock()
    dataset.__iter__.side_effect = lambda: iter([video])
    return cast(VideoDataset, dataset)


def _video(mocker: MockerFixture, video_path: Path) -> VideoSample:
    return cast(
        VideoSample,
        mocker.MagicMock(
            sample_id=uuid4(),
            file_name=video_path.name,
            file_path_abs=str(video_path),
            width=1920,
            height=1080,
            duration_s=60.0,
            fps=30.0,
            sample_table=SimpleNamespace(captions=[]),
        ),
    )


def _local_triplet(tmp_path: Path, stem: str) -> qa_pull.LocalTriplet:
    video_path = tmp_path / f"{stem}.mp4"
    return qa_pull.LocalTriplet(
        bucket="bucket",
        prefix="review",
        stem=stem,
        video_path=video_path,
        transcript_path=tmp_path / f"{stem}.json",
        metadata_path=None,
        source_files=(f"gs://bucket/review/{stem}.mp4",),
        local_files=(video_path,),
    )


def _remote_triplet(bucket: str, stem: str) -> qa_pull.RemoteTriplet:
    return qa_pull.RemoteTriplet(
        bucket=bucket,
        prefix="review",
        stem=stem,
        files=(f"gs://{bucket}/review/{stem}.mp4",),
    )
