from pathlib import Path
from uuid import uuid4

from pytest_mock import MockerFixture

from auto_qa import screen, storage
from lightly_studio.resolvers import metadata_resolver


def test_deliveries_resumes_completed_video(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    delivery = _delivery(tmp_path)
    video = mocker.MagicMock(
        sample_id=uuid4(),
        file_path_abs=str(delivery.video_path.resolve()),
    )
    dataset = mocker.MagicMock()
    dataset.__iter__.side_effect = lambda: iter([video])
    mocker.patch.object(screen, "_write_provenance")
    mocker.patch.object(screen, "_is_complete", return_value=True)
    run_checks = mocker.patch.object(screen, "_run_checks")
    expected = screen.ScreenResult(file_name="clip.mp4", status="pass", issues="")
    mocker.patch.object(screen, "_read_result", return_value=expected)

    assert screen.deliveries(dataset, [delivery]) == [expected]
    dataset.add_videos_from_path.assert_called_once_with(
        path=delivery.video_path.resolve(),
        embed=False,
        embed_frames=False,
        extract_frames=False,
    )
    run_checks.assert_not_called()


def test_run_checks_marks_complete_last(tmp_path: Path, mocker: MockerFixture) -> None:
    delivery = _delivery(tmp_path)
    video = mocker.MagicMock(sample_id=uuid4())
    dataset = mocker.MagicMock()
    events: list[str] = []
    mocker.patch.object(
        screen,
        "_set_complete",
        side_effect=lambda **kwargs: events.append(f"complete={kwargs['complete']}"),
    )
    mocker.patch.object(
        screen,
        "_write_transcript_metadata",
        side_effect=lambda **_: events.append("transcript"),
    )
    mocker.patch.object(screen, "_score_quality", side_effect=lambda **_: events.append("quality"))
    mocker.patch.object(
        screen,
        "_write_technical_metadata",
        side_effect=lambda **_: events.append("technical"),
    )
    mocker.patch.object(screen, "_write_verdict", side_effect=lambda _: events.append("verdict"))

    screen._run_checks(dataset=dataset, videos=[video], deliveries=[delivery])

    assert events == [
        "complete=False",
        "transcript",
        "quality",
        "technical",
        "verdict",
        "complete=True",
    ]


def test_transcript_metadata_skips_missing_transcript(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    delivery = _delivery(tmp_path, has_transcript=False)
    video = mocker.MagicMock(file_path_abs=str(delivery.video_path.resolve()))
    load = mocker.patch.object(screen.whisper_transcript, "load_whisper_transcript")

    screen._write_transcript_metadata(
        dataset=mocker.MagicMock(),
        videos=[video],
        deliveries=[delivery],
    )

    load.assert_not_called()


def test_write_verdict_ignores_removed_qwen_fields(mocker: MockerFixture) -> None:
    video = mocker.MagicMock(sample_id=uuid4())
    metadata = {
        **dict.fromkeys(screen._REQUIRED_CHECKS, True),
        "blur_score": 50.0,
        "lighting_score": 0.45,
        "motion_score": 3.0,
        "whisper_caption_count": 1,
        "narration_classification_complete": False,
    }
    mocker.patch.object(screen, "_metadata", return_value=metadata)
    update = mocker.patch.object(metadata_resolver, "bulk_update_metadata")

    screen._write_verdict(video)

    written = update.call_args.args[1][0][1]
    assert written["automated_qa_status"] == "pass"
    assert written["automated_qa_issues"] == ""


def _delivery(tmp_path: Path, has_transcript: bool = True) -> storage.LocalDelivery:
    video = tmp_path / "clip.mp4"
    return storage.LocalDelivery(
        bucket="bucket",
        prefix="review",
        stem="clip",
        video_path=video,
        transcript_path=tmp_path / "clip.json" if has_transcript else None,
        source_files=("gs://bucket/review/clip.mp4",),
        local_files=(video,),
    )
