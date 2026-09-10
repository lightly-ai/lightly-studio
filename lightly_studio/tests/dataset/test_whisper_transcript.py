from __future__ import annotations

import json
from pathlib import Path

import pytest

from lightly_studio.dataset import egocentric_qa, whisper_transcript


@pytest.fixture
def transcript_path(tmp_path: Path) -> Path:
    path = tmp_path / "transcript.json"
    path.write_text(
        json.dumps(
            {
                "text": " Pick up the cup. ",
                "language": "en",
                "language_probability": 0.98,
                "duration_s": 10.0,
                "speech_duration_s": 6.5,
                "silences": [
                    {"start": 2.4, "end": 4.0, "duration": 1.6},
                    {"start": 8.0, "end": 10.0, "duration": 2.0},
                ],
                "segments": [
                    {
                        "text": " Pick up the cup. ",
                        "start": -0.1,
                        "end": 2.4,
                        "words": [
                            {"word": " Pick", "start": 0.0, "end": 0.5},
                            {"word": " up", "start": 0.5, "end": 0.8},
                        ],
                    },
                    {"text": "Outside duration", "start": 9.0, "end": 12.0, "words": []},
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_load_whisper_transcript__segments(transcript_path: Path) -> None:
    result = whisper_transcript.load_whisper_transcript(
        transcript_path,
        caption_unit="segment",
        video_duration_s=10.0,
    )

    assert result.text == "Pick up the cup."
    assert result.word_count == 2
    assert result.words_per_minute() == pytest.approx(12.0)
    assert result.words_per_minute(duration_s=20.0) == pytest.approx(6.0)
    assert result.language == "en"
    assert result.language_probability == 0.98
    assert result.speech_duration_s == 6.5
    assert result.silence_duration_s == pytest.approx(3.6)
    assert result.silence_ratio == pytest.approx(0.36)
    assert result.captions == (
        whisper_transcript.TimedTranscriptCaption(
            text="Pick up the cup.", start_time_s=0.0, end_time_s=2.4
        ),
        whisper_transcript.TimedTranscriptCaption(
            text="Outside duration", start_time_s=9.0, end_time_s=10.0
        ),
    )


def test_load_whisper_transcript__word_count_falls_back_to_text(tmp_path: Path) -> None:
    path = tmp_path / "transcript-without-word-timestamps.json"
    path.write_text(
        json.dumps(
            {
                "text": "One two three four",
                "duration_s": 60.0,
                "segments": [{"text": "One two three four", "start": 0.0, "end": 1.0}],
            }
        ),
        encoding="utf-8",
    )

    result = whisper_transcript.load_whisper_transcript(path, caption_unit="segment")

    assert result.word_count == 4
    assert result.words_per_minute() == pytest.approx(4.0)


def test_load_whisper_transcript__words(transcript_path: Path) -> None:
    result = whisper_transcript.load_whisper_transcript(
        transcript_path,
        caption_unit="word",
    )

    assert [caption.text for caption in result.captions] == ["Pick", "up"]
    assert [(caption.start_time_s, caption.end_time_s) for caption in result.captions] == [
        (0.0, 0.5),
        (0.5, 0.8),
    ]


def test_load_whisper_transcript__narration_chunks(tmp_path: Path) -> None:
    path = tmp_path / "narration.json"
    words = [
        (" I", 0.0, 0.2),
        (" tighten", 0.2, 0.5),
        (" the", 0.5, 0.6),
        (" screw.", 0.6, 0.9),
        (" The", 1.0, 1.2),
        (" toolbox", 1.2, 1.5),
        (" is", 1.5, 1.6),
        (" beside", 1.6, 1.8),
        (" me.", 1.8, 2.0),
    ]
    path.write_text(
        json.dumps(
            {
                "text": "I tighten the screw. The toolbox is beside me.",
                "segments": [
                    {
                        "text": "I tighten the screw. The toolbox is beside me.",
                        "start": 0.0,
                        "end": 2.0,
                        "words": [
                            {"word": word, "start": start, "end": end} for word, start, end in words
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = whisper_transcript.load_whisper_transcript(
        path,
        caption_unit="narration_chunk",
    )

    assert result.captions == (
        whisper_transcript.TimedTranscriptCaption(
            text="I tighten the screw.", start_time_s=0.0, end_time_s=0.9
        ),
        whisper_transcript.TimedTranscriptCaption(
            text="The toolbox is beside me.", start_time_s=1.0, end_time_s=2.0
        ),
    )
    assert sum(len(caption.text.split()) for caption in result.captions) == result.word_count


@pytest.mark.parametrize("use_flat_words", [False, True])
def test_load_whisper_transcript__narration_chunks_drop_clamped_inversions(
    tmp_path: Path, use_flat_words: bool
) -> None:
    path = tmp_path / "clamped-narration.json"
    words = [
        (" I", 0.0, 0.2),
        (" tighten", 0.2, 0.5),
        (" the", 0.5, 0.6),
        (" screw.", 0.6, 0.9),
        (" The", 5.0, 5.2),
        (" toolbox", 5.2, 5.5),
        (" is", 5.5, 5.6),
        (" beside", 5.6, 5.8),
        (" me.", 5.8, 6.0),
    ]
    word_dicts = [{"word": word, "start": start, "end": end} for word, start, end in words]
    payload: dict[str, object] = {"text": "I tighten the screw. The toolbox is beside me."}
    if use_flat_words:
        payload["words"] = word_dicts
    else:
        payload["segments"] = [{"text": "", "start": 0.0, "end": 6.0, "words": word_dicts}]
    path.write_text(json.dumps(payload), encoding="utf-8")

    result = whisper_transcript.load_whisper_transcript(
        path,
        caption_unit="narration_chunk",
        video_duration_s=2.0,
    )

    assert all(caption.start_time_s < caption.end_time_s for caption in result.captions)
    assert result.captions == (
        whisper_transcript.TimedTranscriptCaption(
            text="I tighten the screw.", start_time_s=0.0, end_time_s=0.9
        ),
    )


def test_load_whisper_transcript__narration_chunks_limit_long_phrases(tmp_path: Path) -> None:
    path = tmp_path / "long-narration.json"
    words = [
        {"word": f" word{index}", "start": index * 0.1, "end": (index + 1) * 0.1}
        for index in range(35)
    ]
    path.write_text(
        json.dumps(
            {
                "text": " ".join(f"word{index}" for index in range(35)),
                "segments": [{"text": "long", "start": 0.0, "end": 3.5, "words": words}],
            }
        ),
        encoding="utf-8",
    )

    result = whisper_transcript.load_whisper_transcript(
        path,
        caption_unit="narration_chunk",
    )

    assert [len(caption.text.split()) for caption in result.captions] == [30, 5]
    assert result.captions[0].end_time_s <= result.captions[1].start_time_s


def test_load_whisper_transcript__action_phrases(tmp_path: Path) -> None:
    path = tmp_path / "actions.json"
    words = [
        (" Now", 0.0, 0.2),
        (" I", 0.2, 0.3),
        (" pick", 0.3, 0.6),
        (" up", 0.6, 0.8),
        (" the", 0.8, 0.9),
        (" red", 0.9, 1.1),
        (" shirt", 1.1, 1.4),
        (" and", 1.4, 1.5),
        (" then", 1.5, 1.7),
        (" folding", 1.7, 2.0),
        (" it", 2.0, 2.1),
        (" carefully.", 2.1, 2.4),
        (" This", 4.0, 4.2),
        (" looks", 4.2, 4.4),
        (" nice.", 4.4, 4.7),
    ]
    path.write_text(
        json.dumps(
            {
                "segments": [
                    {
                        "text": "Now I pick up the red shirt and then fold it carefully.",
                        "start": 0.0,
                        "end": 4.7,
                        "words": [
                            {"word": word, "start": start, "end": end} for word, start, end in words
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = whisper_transcript.load_whisper_transcript(
        path,
        caption_unit="action_phrase",
        video_duration_s=5.0,
    )

    assert [caption.text for caption in result.captions] == [
        "pick up the red shirt",
        "fold it carefully",
    ]
    assert [(caption.start_time_s, caption.end_time_s) for caption in result.captions] == [
        pytest.approx((0.0, 2.5)),
        pytest.approx((0.7, 3.4)),
    ]


def test_load_whisper_transcript__action_phrase_splits_on_pause(tmp_path: Path) -> None:
    path = tmp_path / "paused-action.json"
    path.write_text(
        json.dumps(
            {
                "segments": [
                    {
                        "text": "Open the box. Put down the lid.",
                        "start": 3.0,
                        "end": 7.0,
                        "words": [
                            {"word": " Open", "start": 3.0, "end": 3.3},
                            {"word": " the", "start": 3.3, "end": 3.4},
                            {"word": " box", "start": 3.4, "end": 3.7},
                            {"word": " put", "start": 5.0, "end": 5.2},
                            {"word": " down", "start": 5.2, "end": 5.4},
                            {"word": " the", "start": 5.4, "end": 5.5},
                            {"word": " lid.", "start": 5.5, "end": 5.8},
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = whisper_transcript.load_whisper_transcript(
        path,
        caption_unit="action_phrase",
        action_phrase_settings=whisper_transcript.ActionPhraseSettings(
            window_padding_s=0.0,
            min_window_duration_s=0.5,
        ),
    )

    assert [caption.text for caption in result.captions] == [
        "open the box",
        "put down the lid",
    ]


def test_load_whisper_transcript__missing_segments(tmp_path: Path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="segments list"):
        whisper_transcript.load_whisper_transcript(path)


def test_parse_whisper_transcript__matches_load_whisper_transcript(
    transcript_path: Path,
) -> None:
    payload = json.loads(transcript_path.read_text(encoding="utf-8"))

    assert whisper_transcript.parse_whisper_transcript(
        payload=payload, caption_unit="word"
    ) == whisper_transcript.load_whisper_transcript(transcript_path, caption_unit="word")


def test_parse_whisper_transcript__non_object_payload() -> None:
    with pytest.raises(ValueError, match="must be a JSON object"):
        whisper_transcript.parse_whisper_transcript(payload=["not", "an", "object"])


def test_parse_whisper_transcript__non_list_segment_words() -> None:
    # A vendor shipping a scalar under ``words`` used to raise TypeError from the
    # duration and silence derivations, which never reach the ``_get_words`` guard.
    result = whisper_transcript.parse_whisper_transcript(
        payload={"segments": [{"text": "Hi.", "start": 0.0, "end": 1.0, "words": 5}]},
    )

    assert result.duration_s is None
    assert result.silences == ()
    assert [caption.text for caption in result.captions] == ["Hi."]


def test_transcript_from_document__reads_every_field_verbatim() -> None:
    document = {
        "text": " Pick up the cup. ",
        "language": "en",
        "language_probability": 0.98,
        "word_count": 4,
        "duration_s": 10.0,
        "speech_duration_s": 6.5,
        "silences": [{"start": 2.4, "end": 4.0}],
        "captions": [{"text": "Pick up the cup.", "start": 0.0, "end": 2.4}],
    }

    result = whisper_transcript.transcript_from_document(document)

    assert result == whisper_transcript.WhisperTranscript(
        text="Pick up the cup.",
        word_count=4,
        language="en",
        language_probability=0.98,
        duration_s=10.0,
        speech_duration_s=6.5,
        silences=(whisper_transcript.SilenceSpan(start_time_s=2.4, end_time_s=4.0),),
        captions=(
            whisper_transcript.TimedTranscriptCaption(
                text="Pick up the cup.", start_time_s=0.0, end_time_s=2.4
            ),
        ),
    )


def test_load_whisper_transcript__keeps_zero_duration_words(tmp_path: Path) -> None:
    # Vendors emit zero-duration words for fast speech. They used to be dropped,
    # which silently deleted them from the narration text.
    path = tmp_path / "zero_duration.json"
    path.write_text(
        json.dumps(
            {
                "text": "I am wiping eggs",
                "words": [
                    {"word": "I", "start": 0.0, "end": 0.4},
                    {"word": "am", "start": 0.4, "end": 0.8},
                    {"word": "wiping", "start": 0.8, "end": 0.8},
                    {"word": "eggs", "start": 0.8, "end": 1.6},
                ],
            }
        ),
        encoding="utf-8",
    )

    result = whisper_transcript.load_whisper_transcript(path, caption_unit="narration_chunk")

    assert [caption.text for caption in result.captions] == ["I am wiping eggs"]


def test_load_whisper_transcript__drops_inverted_words(tmp_path: Path) -> None:
    path = tmp_path / "inverted.json"
    path.write_text(
        json.dumps(
            {
                "text": "I am wiping",
                "words": [
                    {"word": "I", "start": 0.0, "end": 0.4},
                    {"word": "am", "start": 2.0, "end": 1.0},
                    {"word": "wiping", "start": 0.4, "end": 1.6},
                ],
            }
        ),
        encoding="utf-8",
    )

    result = whisper_transcript.load_whisper_transcript(path, caption_unit="narration_chunk")

    assert [caption.text for caption in result.captions] == ["I wiping"]


def test_load_whisper_transcript__reads_a_vtt_as_one_caption_per_cue(tmp_path: Path) -> None:
    path = tmp_path / "clip.vtt"
    path.write_text(
        "WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nI pick up the pan.\n"
        "\n00:00:02.000 --> 00:00:04.000\nI add the oil.\n",
        encoding="utf-8",
    )

    result = whisper_transcript.load_whisper_transcript(path, caption_unit="narration_chunk")

    assert [caption.text for caption in result.captions] == ["I pick up the pan.", "I add the oil."]
    # Requested narration chunks, but a cue-timed source has no words to chunk on.
    assert result.caption_unit == "segment"


def test_load_whisper_transcript__counts_vtt_words_from_the_text(tmp_path: Path) -> None:
    path = tmp_path / "clip.vtt"
    path.write_text(
        "WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nI pick up the pan.\n", encoding="utf-8"
    )

    result = whisper_transcript.load_whisper_transcript(path, caption_unit="narration_chunk")

    assert result.word_count == 5
    assert result.words_per_minute(duration_s=60.0) == 5.0


def test_load_whisper_transcript__leaves_vtt_word_statistics_unset(tmp_path: Path) -> None:
    # WebVTT has no per-word timings, so these are reported as unknown rather than
    # synthesized: they reach the client as delivered transcript columns.
    path = tmp_path / "clip.vtt"
    path.write_text(
        "WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nI pick up the pan.\n", encoding="utf-8"
    )

    result = whisper_transcript.load_whisper_transcript(path, caption_unit="narration_chunk")

    assert result.duration_s is None
    assert result.speech_duration_s is None
    assert result.silences == ()
    assert result.silence_ratio is None


def test_load_whisper_transcript__vtt_captions_pass_the_timestamp_check(tmp_path: Path) -> None:
    # ``qa_transcript_timestamps_valid`` is a blocking check, so a promoted Ayadata
    # video must clear it on cue timings alone.
    path = tmp_path / "clip.vtt"
    path.write_text(
        "WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nOne.\n\n00:00:02.000 --> 00:00:04.000\nTwo.\n",
        encoding="utf-8",
    )

    result = whisper_transcript.load_whisper_transcript(
        path, caption_unit="segment", video_duration_s=10.0
    )

    assert egocentric_qa.has_valid_caption_timestamps(captions=result.captions, duration_s=10.0)


def test_load_whisper_transcript__reads_the_vtt_language_header(tmp_path: Path) -> None:
    path = tmp_path / "clip.vtt"
    path.write_text(
        "WEBVTT\nLanguage: en\n\n00:00:00.000 --> 00:00:01.000\nHi.\n", encoding="utf-8"
    )

    result = whisper_transcript.load_whisper_transcript(path)

    assert result.language == "en"


def test_load_whisper_transcript__reports_the_requested_unit_when_words_exist(
    tmp_path: Path,
) -> None:
    path = tmp_path / "clip_transcript.json"
    path.write_text(
        json.dumps(
            {
                "text": "I pick up the pan.",
                "segments": [
                    {
                        "text": "I pick up the pan.",
                        "start": 0.0,
                        "end": 2.0,
                        "words": [
                            {"word": "I", "start": 0.0, "end": 0.4},
                            {"word": "pick", "start": 0.4, "end": 0.8},
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = whisper_transcript.load_whisper_transcript(path, caption_unit="narration_chunk")

    assert result.caption_unit == "narration_chunk"
