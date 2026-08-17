from pathlib import Path

from pytest_mock import MockerFixture

from auto_qa import storage, transcribe


def test_missing_transcripts_tracks_generated_file(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    video = tmp_path / "clip.mp4"
    python = tmp_path / "python"
    video.write_bytes(b"video")
    python.write_text("")
    delivery = storage.LocalDelivery(
        bucket="bucket",
        prefix="review",
        stem="clip",
        video_path=video,
        transcript_path=None,
        source_files=("gs://bucket/review/clip.mp4",),
        local_files=(video,),
    )
    mocker.patch.object(transcribe, "_run")

    result = transcribe.missing_transcripts([delivery], python=python)

    output = tmp_path / "clip.faster-whisper.json"
    assert result[0].transcript_path == output
    assert result[0].local_files == (video, output)
