from pathlib import Path

import pytest

from scripts import qa_pull, qa_transcribe


def test_fill_missing_transcripts__tracks_generated_file_for_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    video_path = tmp_path / "clip.mp4"
    video_path.write_bytes(b"video")
    whisper_python = tmp_path / "python"
    whisper_python.write_text("")
    triplet = qa_pull.LocalTriplet(
        bucket="bucket",
        prefix="review",
        stem="clip",
        video_path=video_path,
        transcript_path=None,
        metadata_path=None,
        source_files=("gs://bucket/review/clip.mp4",),
        local_files=(video_path,),
    )
    monkeypatch.setattr(qa_transcribe, "_run_whisper", lambda **_: None)

    result = qa_transcribe.fill_missing_transcripts(
        triplets=[triplet],
        whisper_python=whisper_python,
    )

    transcript_path = tmp_path / "clip.faster-whisper.json"
    assert result[0].transcript_path == transcript_path
    assert result[0].local_files == (video_path, transcript_path)
