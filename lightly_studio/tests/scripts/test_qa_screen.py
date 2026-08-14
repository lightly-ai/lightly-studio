from pathlib import Path
from uuid import uuid4

import pytest
from pytest_mock import MockerFixture

from lightly_studio.resolvers import metadata_resolver
from scripts import qa_pull, qa_screen, run_egocentric_qa


def test_chunks__splits_into_full_and_remainder() -> None:
    chunks = qa_screen._chunks(list(range(7)), size=3)

    assert chunks == [[0, 1, 2], [3, 4, 5], [6]]


def test_chunks__empty_input() -> None:
    assert qa_screen._chunks([], size=3) == []


@pytest.mark.parametrize("size", [0, -1])
def test_chunks__rejects_non_positive_size(size: int) -> None:
    with pytest.raises(ValueError, match="batch_size"):
        qa_screen._chunks([1, 2, 3], size=size)


def test_screen_deliveries__resumes_existing_completed_video_without_reprocessing(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    triplet = _local_triplet(tmp_path=tmp_path)
    video = mocker.MagicMock(
        sample_id=uuid4(),
        file_path_abs=str(triplet.video_path.resolve()),
    )
    dataset = mocker.MagicMock()
    dataset.__iter__.side_effect = lambda: iter([video])
    mocker.patch.object(qa_screen, "_write_provenance")
    mocker.patch.object(qa_screen, "_pipeline_complete", return_value=True)
    probe = mocker.patch.object(run_egocentric_qa, "_probe_narration_classifier")
    screen_videos = mocker.patch.object(qa_screen, "_screen_videos")
    expected = qa_screen.ScreenResult(
        file_name="clip.mp4",
        automated_qa_status="pass",
        narration_qa_status="likely_pass",
        issues="",
    )
    mocker.patch.object(qa_screen, "_read_result", return_value=expected)

    results = qa_screen.screen_deliveries(
        dataset=dataset,
        triplets=[triplet],
        classifier=mocker.MagicMock(),
    )

    assert results == [expected]
    dataset.add_videos_from_path.assert_called_once_with(
        path=triplet.video_path.resolve(),
        embed=False,
        embed_frames=False,
        target_fps=qa_screen.DEFAULT_TARGET_FPS,
    )
    probe.assert_not_called()
    screen_videos.assert_not_called()


def test_screen_videos__marks_complete_after_file_dependent_checks(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    triplet = _local_triplet(tmp_path=tmp_path)
    video = mocker.MagicMock(sample_id=uuid4())
    dataset = mocker.MagicMock()
    events: list[str] = []
    mocker.patch.object(
        run_egocentric_qa,
        "_create_transcript_captions",
        side_effect=lambda **_: _record_and_return_empty(events=events, event="captions"),
    )
    mocker.patch.object(
        run_egocentric_qa,
        "_classify_narration_captions",
        side_effect=lambda **_: events.append("classification"),
    )
    mocker.patch.object(
        qa_screen,
        "_score_quality",
        side_effect=lambda **_: events.append("quality"),
    )
    mocker.patch.object(
        run_egocentric_qa,
        "_write_technical_qa_metadata",
        side_effect=lambda **_: events.append("technical"),
    )
    mocker.patch.object(
        run_egocentric_qa,
        "_write_qa_summary",
        side_effect=lambda **_: events.append("summary"),
    )
    metadata_update = mocker.patch.object(
        metadata_resolver,
        "bulk_update_metadata",
        side_effect=lambda *_: events.append("complete"),
    )

    qa_screen._screen_videos(
        dataset=dataset,
        batch=[triplet],
        videos=[video],
        classifier=mocker.MagicMock(),
        caption_unit=qa_screen.DEFAULT_CAPTION_UNIT,
        action_phrase_settings=qa_screen.DEFAULT_ACTION_PHRASE_SETTINGS,
        force=False,
    )

    assert events == [
        "complete",
        "captions",
        "classification",
        "quality",
        "technical",
        "summary",
        "complete",
    ]
    assert metadata_update.call_args_list == [
        mocker.call(
            dataset.session,
            [(video.sample_id, {qa_screen.PIPELINE_COMPLETE_KEY: False})],
        ),
        mocker.call(
            dataset.session,
            [(video.sample_id, {qa_screen.PIPELINE_COMPLETE_KEY: True})],
        ),
    ]


def test_validate_transcripts__reports_delivery_identity(tmp_path: Path) -> None:
    triplet = _local_triplet(tmp_path=tmp_path, has_transcript=False)

    with pytest.raises(ValueError, match="bucket/review/clip"):
        qa_screen._validate_transcripts(triplets=[triplet])


def test_write_qa_summary__does_not_review_narration_above_requirement(
    mocker: MockerFixture,
) -> None:
    video = mocker.MagicMock(sample_id=uuid4())
    video.get_object_session.return_value = mocker.sentinel.session
    metadata = {
        "qa_resolution_pass": True,
        "qa_duration_pass": True,
        "qa_has_audio": True,
        "qa_has_narration": True,
        "whisper_wpm_pass": True,
        "qa_transcript_timestamps_valid": True,
        "narration_classification_complete": True,
        "narration_requirement_pass": True,
        "blur_score": 50.0,
        "lighting_score": 0.45,
        "motion_score": 3.0,
        "whisper_caption_count": 1,
        "repeated_caption_group_count": 0,
        "narration_qa_status": "manual_review",
        "narration_qualifying_percentage": 70.0,
    }
    mocker.patch.object(
        metadata_resolver,
        "get_value_for_sample",
        side_effect=lambda *, key, **_: metadata.get(key),
    )
    update = mocker.patch.object(metadata_resolver, "bulk_update_metadata")

    run_egocentric_qa._write_qa_summary(
        video=video,
        include_legacy_caption_threshold=False,
    )

    written_metadata = update.call_args.args[1][0][1]
    assert written_metadata["automated_qa_status"] == "pass"
    assert written_metadata["automated_qa_review_issues"] == ""
    assert written_metadata["automated_qa_review_issue_count"] == 0


def _local_triplet(tmp_path: Path, has_transcript: bool = True) -> qa_pull.LocalTriplet:
    video_path = tmp_path / "clip.mp4"
    transcript_path = tmp_path / "clip.json" if has_transcript else None
    return qa_pull.LocalTriplet(
        bucket="bucket",
        prefix="review",
        stem="clip",
        video_path=video_path,
        transcript_path=transcript_path,
        metadata_path=None,
        source_files=("gs://bucket/review/clip.mp4",),
        local_files=(video_path,),
    )


def _record_and_return_empty(events: list[str], event: str) -> list[object]:
    events.append(event)
    return []
