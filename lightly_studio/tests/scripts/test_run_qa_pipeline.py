from __future__ import annotations

import argparse
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from lightly_studio.core.video.video_dataset import VideoDataset
from lightly_studio.database import db_manager
from scripts import (
    qa_pull,
    qa_results,
    qa_screen,
    run_egocentric_qa,
    run_qa_pipeline,
    sample_gcs_review,
)


def test_main__downloads_and_cleans_one_batch_at_a_time(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    args = _args(tmp_path=tmp_path, cleanup_local_files=True)
    remote = [_remote_triplet(stem="first"), _remote_triplet(stem="second")]
    local = [_local_triplet(tmp_path=tmp_path, stem=triplet.stem) for triplet in remote]
    _mock_pipeline_setup(mocker=mocker, args=args, remote=remote)
    download = mocker.patch.object(
        qa_pull,
        "download_triplets",
        side_effect=[[local[0]], [local[1]]],
    )
    mocker.patch.object(run_qa_pipeline, "_transcribe_batch", side_effect=_identity_transcribe)
    mocker.patch.object(qa_screen, "screen_deliveries", return_value=[])
    cleanup = mocker.patch.object(qa_pull, "cleanup_triplets", return_value=1)

    run_qa_pipeline.main()

    assert [call.kwargs["triplets"] for call in download.call_args_list] == [
        [remote[0]],
        [remote[1]],
    ]
    assert [call.kwargs["triplets"] for call in cleanup.call_args_list] == [
        [local[0]],
        [local[1]],
    ]


def test_main__isolates_failed_batch(
    tmp_path: Path,
    mocker: MockerFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    args = _args(tmp_path=tmp_path, cleanup_local_files=True)
    remote = [_remote_triplet(stem="clip")]
    local = [_local_triplet(tmp_path=tmp_path, stem="clip")]
    _mock_pipeline_setup(mocker=mocker, args=args, remote=remote)
    mocker.patch.object(qa_pull, "download_triplets", return_value=local)
    mocker.patch.object(run_qa_pipeline, "_transcribe_batch", return_value=local)
    mocker.patch.object(
        qa_screen,
        "screen_deliveries",
        side_effect=RuntimeError("screening failed"),
    )
    cleanup = mocker.patch.object(qa_pull, "cleanup_triplets", return_value=1)

    run_qa_pipeline.main()

    cleanup.assert_called_once_with(triplets=local, destination=args.destination)
    output = capsys.readouterr().out
    assert "Batch 1 failed: screening failed" in output
    assert "1 batch(es) failed" in output


def test_main__processes_one_bucket_at_a_time(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    args = _args(tmp_path=tmp_path, cleanup_local_files=False)
    args.batch_size = 8
    remote = [
        _remote_triplet(stem="first", bucket="first-bucket"),
        _remote_triplet(stem="second", bucket="second-bucket"),
    ]
    _mock_pipeline_setup(mocker=mocker, args=args, remote=remote)
    process_batch = mocker.patch.object(run_qa_pipeline, "_process_batch")

    run_qa_pipeline.main()

    assert [call.kwargs["batch"] for call in process_batch.call_args_list] == [
        [remote[0]],
        [remote[1]],
    ]


def test_main__upload_failure_cleans_batch_files(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    args = _args(tmp_path=tmp_path, cleanup_local_files=True)
    args.apply = True
    remote = [_remote_triplet(stem="clip")]
    local = [_local_triplet(tmp_path=tmp_path, stem="clip")]
    _mock_pipeline_setup(mocker=mocker, args=args, remote=remote)
    mocker.patch.object(qa_results, "filter_unpublished_triplets", return_value=remote)
    mocker.patch.object(qa_pull, "download_triplets", return_value=local)
    mocker.patch.object(run_qa_pipeline, "_transcribe_batch", return_value=local)
    mocker.patch.object(qa_screen, "screen_deliveries", return_value=[])
    mocker.patch.object(
        qa_results,
        "upload_result_records",
        side_effect=RuntimeError("upload failed"),
    )
    cleanup = mocker.patch.object(qa_pull, "cleanup_triplets", return_value=1)

    run_qa_pipeline.main()

    cleanup.assert_called_once_with(triplets=local, destination=args.destination)


def _mock_pipeline_setup(
    mocker: MockerFixture,
    args: argparse.Namespace,
    remote: list[qa_pull.RemoteTriplet],
) -> None:
    mocker.patch.object(run_qa_pipeline, "_parse_args", return_value=args)
    mocker.patch.object(sample_gcs_review, "_storage_client", return_value=mocker.MagicMock())
    mocker.patch.object(qa_pull, "discover_triplets", return_value=remote)
    mocker.patch.object(db_manager, "connect")
    mocker.patch.object(VideoDataset, "load_or_create", return_value=mocker.MagicMock())
    mocker.patch.object(qa_screen, "build_classifier", return_value=mocker.MagicMock())
    mocker.patch.object(run_egocentric_qa, "_probe_narration_classifier")
    mocker.patch.object(qa_screen, "write_dataset_summary")


def _args(tmp_path: Path, cleanup_local_files: bool) -> argparse.Namespace:
    return argparse.Namespace(
        project="project",
        bucket=None,
        bucket_suffix="-qa",
        work_prefix=["review", "pool"],
        max_videos=None,
        dry_run=False,
        destination=tmp_path,
        cleanup_local_files=cleanup_local_files,
        apply=False,
        results_prefix=qa_results.DEFAULT_RESULTS_PREFIX,
        db_file=tmp_path / "qa.db",
        dataset_name="egocentric-qa",
        narration_llm_base_url="http://localhost:11434",
        narration_llm_model="qwen3:8b",
        narration_llm_provider="ollama",
        narration_llm_api_key=None,
        classification_batch_size=8,
        batch_size=1,
        target_fps=1.0,
        force_classify=False,
    )


def _identity_transcribe(
    args: argparse.Namespace,
    triplets: list[qa_pull.LocalTriplet],
) -> list[qa_pull.LocalTriplet]:
    del args
    return triplets


def _remote_triplet(stem: str, bucket: str = "bucket") -> qa_pull.RemoteTriplet:
    return qa_pull.RemoteTriplet(
        bucket=bucket,
        prefix="review",
        stem=stem,
        files=(f"gs://{bucket}/review/{stem}.mp4",),
    )


def _local_triplet(tmp_path: Path, stem: str) -> qa_pull.LocalTriplet:
    video_path = tmp_path / f"{stem}.mp4"
    transcript_path = tmp_path / f"{stem}.json"
    return qa_pull.LocalTriplet(
        bucket="bucket",
        prefix="review",
        stem=stem,
        video_path=video_path,
        transcript_path=transcript_path,
        metadata_path=None,
        source_files=(f"gs://bucket/review/{stem}.mp4",),
        local_files=(video_path, transcript_path),
    )
