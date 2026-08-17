from __future__ import annotations

import argparse
from pathlib import Path

from pytest_mock import MockerFixture

from auto_qa import pipeline, results, screen, storage, transcribe
from lightly_studio.core.video.video_dataset import VideoDataset
from lightly_studio.database import db_manager


def test_main_processes_and_cleans_one_batch_at_a_time(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    args = _args(tmp_path, cleanup_local_files=True, batch_size=1)
    remote = [_remote("first"), _remote("second")]
    local = [_local(tmp_path, delivery.stem) for delivery in remote]
    _mock_setup(mocker, args=args, remote=remote)
    download = mocker.patch.object(storage, "download", side_effect=[[local[0]], [local[1]]])
    mocker.patch.object(screen, "deliveries", return_value=[])
    cleanup = mocker.patch.object(storage, "cleanup", return_value=2)

    assert pipeline.main() == 0
    assert [call.kwargs["deliveries"] for call in download.call_args_list] == [
        [remote[0]],
        [remote[1]],
    ]
    assert [call.kwargs["deliveries"] for call in cleanup.call_args_list] == [
        [local[0]],
        [local[1]],
    ]


def test_main_keeps_files_and_returns_failure_for_failed_batch(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    args = _args(tmp_path, cleanup_local_files=True)
    remote = [_remote("clip")]
    _mock_setup(mocker, args=args, remote=remote)
    mocker.patch.object(storage, "download", return_value=[_local(tmp_path, "clip")])
    mocker.patch.object(screen, "deliveries", side_effect=RuntimeError("screening failed"))
    cleanup = mocker.patch.object(storage, "cleanup")

    assert pipeline.main() == 1
    cleanup.assert_not_called()


def test_main_only_runs_whisper_when_enabled(tmp_path: Path, mocker: MockerFixture) -> None:
    args = _args(tmp_path, transcribe_missing=True)
    remote = [_remote("clip")]
    local = [_local(tmp_path, "clip")]
    _mock_setup(mocker, args=args, remote=remote)
    mocker.patch.object(storage, "download", return_value=local)
    run_whisper = mocker.patch.object(transcribe, "missing_transcripts", return_value=local)
    mocker.patch.object(screen, "deliveries", return_value=[])

    assert pipeline.main() == 0
    run_whisper.assert_called_once()


def _mock_setup(
    mocker: MockerFixture,
    args: argparse.Namespace,
    remote: list[storage.RemoteDelivery],
) -> None:
    mocker.patch.object(pipeline, "_parse_args", return_value=args)
    mocker.patch.object(storage, "create_client", return_value=mocker.MagicMock())
    mocker.patch.object(storage, "discover", return_value=remote)
    mocker.patch.object(db_manager, "connect")
    mocker.patch.object(VideoDataset, "load_or_create", return_value=mocker.MagicMock())
    mocker.patch.object(screen, "write_dataset_summary")


def _args(tmp_path: Path, **overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "project": "project",
        "bucket": None,
        "bucket_suffix": "-qa",
        "prefix": ["review", "pool"],
        "destination": tmp_path,
        "db_file": tmp_path / "qa.db",
        "dataset_name": "egocentric-qa",
        "results_prefix": results.DEFAULT_PREFIX,
        "batch_size": 16,
        "max_videos": None,
        "dry_run": False,
        "apply": False,
        "force": False,
        "cleanup_local_files": False,
        "transcribe_missing": False,
        "whisper_python": transcribe.DEFAULT_PYTHON,
        "whisper_model": transcribe.DEFAULT_MODEL,
        "whisper_device": transcribe.DEFAULT_DEVICE,
        "whisper_compute_type": transcribe.DEFAULT_COMPUTE_TYPE,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def _remote(stem: str) -> storage.RemoteDelivery:
    return storage.RemoteDelivery(
        bucket="bucket",
        prefix="review",
        stem=stem,
        files=(f"gs://bucket/review/{stem}.mp4",),
    )


def _local(tmp_path: Path, stem: str) -> storage.LocalDelivery:
    video = tmp_path / f"{stem}.mp4"
    transcript_path = tmp_path / f"{stem}.json"
    return storage.LocalDelivery(
        bucket="bucket",
        prefix="review",
        stem=stem,
        video_path=video,
        transcript_path=transcript_path,
        source_files=(f"gs://bucket/review/{stem}.mp4",),
        local_files=(video, transcript_path),
    )
