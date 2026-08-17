from __future__ import annotations

import json
import math
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pytest_mock import MockerFixture

from auto_qa import results, screen, storage
from lightly_studio.resolvers import metadata_resolver


def test_build_creates_schema_without_qwen_fields(tmp_path: Path, mocker: MockerFixture) -> None:
    delivery = _local(tmp_path, stem="nested/clip")
    video = _video(mocker, delivery.video_path)
    dataset = _dataset(mocker, video)
    metadata = {
        screen.COMPLETE_KEY: True,
        "automated_qa_status": "review",
        "automated_qa_failures": "",
        "automated_qa_review_issues": "blurry",
        "expected_quality_label": "accepted",
        "qa_resolution_pass": True,
        "qa_duration_pass": True,
        "qa_has_audio": True,
        "qa_has_narration": True,
        "qa_transcript_timestamps_valid": True,
        "whisper_words_per_minute": 80.0,
        "whisper_wpm_pass": True,
        "whisper_caption_count": 2,
        "narration_classification_complete": True,
        "narration_qualifying_percentage": 70.0,
        "narration_qa_status": "manual_review",
        "blur_score": 23.4,
        "custom_future_metric": 42,
    }
    caption_id = uuid4()
    video.sample_table.captions = [
        SimpleNamespace(
            sample_id=caption_id,
            text="I pick up the shirt.",
            temporal_span_details=SimpleNamespace(start_time_s=1.5, end_time_s=3.0),
            metadata_dict=SimpleNamespace(data={"narration_label": "TASK"}),
        )
    ]
    mocker.patch.object(
        metadata_resolver,
        "get_by_sample_id",
        return_value=SimpleNamespace(data=metadata),
    )

    _, name, record = results.build(dataset, [delivery])[0]

    assert name == "automated_qa_results/clip_results.json"
    assert record["schema_version"] == 2
    assert record["verdict"] == {
        "status": "review",
        "expected_quality_label": "accepted",
        "failures": [],
        "failure_count": 0,
        "review_issues": ["blurry"],
        "review_issue_count": 1,
        "issues": ["blurry"],
        "issue_count": 1,
    }
    assert record["source"]["video_url"] == "gs://bucket/review/nested/clip.mp4"
    assert record["video"]["file_path_abs"] == str(delivery.video_path)
    assert record["checks"]["task_environment_narration"]["status"] == "pass"
    assert record["checks"]["blur"]["status"] == "fail"
    assert record["metrics"]["narration"]["qa_status"] == "manual_review"
    assert record["metrics"]["other"] == {"custom_future_metric": 42}
    assert record["narration_chunks"] == [
        {
            "sample_id": str(caption_id),
            "text": "I pick up the shirt.",
            "start_time_s": 1.5,
            "end_time_s": 3.0,
            "metadata": {"narration_label": "TASK"},
        }
    ]


def test_build_keeps_qwen_checks_as_not_run_when_metadata_is_absent(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    delivery = _local(tmp_path)
    video = _video(mocker, delivery.video_path)
    dataset = _dataset(mocker, video)
    mocker.patch.object(
        metadata_resolver,
        "get_by_sample_id",
        return_value=SimpleNamespace(
            data={screen.COMPLETE_KEY: True, "automated_qa_status": "pass"}
        ),
    )

    record = results.build(dataset, [delivery])[0][2]

    assert record["checks"]["narration_classification"]["status"] == "not_run"
    assert record["checks"]["task_environment_narration"]["status"] == "not_run"


def test_build_rejects_incomplete_video(tmp_path: Path, mocker: MockerFixture) -> None:
    delivery = _local(tmp_path)
    video = _video(mocker, delivery.video_path)
    dataset = _dataset(mocker, video)
    mocker.patch.object(
        metadata_resolver,
        "get_by_sample_id",
        return_value=SimpleNamespace(data={screen.COMPLETE_KEY: False}),
    )

    with pytest.raises(RuntimeError, match="incomplete QA result"):
        results.build(dataset, [delivery])


def test_upload_writes_strict_json(tmp_path: Path, mocker: MockerFixture) -> None:
    delivery = _local(tmp_path)
    client = mocker.MagicMock()
    mocker.patch.object(
        results,
        "build",
        return_value=[(delivery, "automated_qa_results/clip_results.json", {"score": math.nan})],
    )

    urls = results.upload(client, mocker.MagicMock(), [delivery])

    assert urls == ["gs://bucket/automated_qa_results/clip_results.json"]
    payload = client.bucket.return_value.blob.return_value.upload_from_string.call_args.args[0]
    assert json.loads(payload) == {"score": None}


def test_unpublished_lists_each_bucket_once(mocker: MockerFixture) -> None:
    published = _remote("first", "published")
    pending = _remote("first", "pending")
    other = _remote("second", "other")
    client = mocker.MagicMock()
    client.list_blobs.side_effect = [
        [SimpleNamespace(name="automated_qa_results/published_results.json")],
        [],
    ]

    assert results.unpublished(client, [published, pending, other]) == [pending, other]
    assert client.list_blobs.call_count == 2


def _dataset(mocker: MockerFixture, video: object) -> object:
    dataset = mocker.MagicMock()
    dataset.__iter__.side_effect = lambda: iter([video])
    return dataset


def _video(mocker: MockerFixture, path: Path) -> object:
    return mocker.MagicMock(
        sample_id=uuid4(),
        file_name=path.name,
        file_path_abs=str(path),
        width=1920,
        height=1080,
        duration_s=60.0,
        fps=30.0,
        sample_table=SimpleNamespace(captions=[]),
    )


def _local(tmp_path: Path, stem: str = "clip") -> storage.LocalDelivery:
    video = tmp_path / f"{stem}.mp4"
    return storage.LocalDelivery(
        bucket="bucket",
        prefix="review",
        stem=stem,
        video_path=video,
        transcript_path=tmp_path / f"{stem}.json",
        source_files=(f"gs://bucket/review/{stem}.mp4",),
        local_files=(video,),
    )


def _remote(bucket: str, stem: str) -> storage.RemoteDelivery:
    return storage.RemoteDelivery(
        bucket=bucket,
        prefix="review",
        stem=stem,
        files=(f"gs://{bucket}/review/{stem}.mp4",),
    )
