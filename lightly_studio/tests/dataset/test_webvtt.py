from __future__ import annotations

import pytest

from lightly_studio.dataset import webvtt


def test_parse_webvtt__reads_cues_as_segments() -> None:
    text = "WEBVTT\n\n00:00:00.000 --> 00:00:02.500\nI pick up the pan.\n"

    payload = webvtt.parse_webvtt(text=text, source="clip.vtt")

    assert payload["segments"] == [
        {"text": "I pick up the pan.", "start": 0.0, "end": 2.5},
    ]
    assert payload["text"] == "I pick up the pan."


def test_parse_webvtt__carries_no_word_timings() -> None:
    # WebVTT times whole cues. Nothing downstream may report a per-word statistic
    # derived from a cue, so the adapter must not invent a ``words`` list.
    text = "WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nI pick up the pan.\n"

    payload = webvtt.parse_webvtt(text=text, source="clip.vtt")

    assert "words" not in payload["segments"][0]


def test_parse_webvtt__skips_a_cue_identifier() -> None:
    text = "WEBVTT\n\ncue-1\n00:00:01.000 --> 00:00:02.000\nHello.\n"

    payload = webvtt.parse_webvtt(text=text, source="clip.vtt")

    assert payload["segments"] == [{"text": "Hello.", "start": 1.0, "end": 2.0}]


def test_parse_webvtt__reads_the_short_timestamp_form() -> None:
    text = "WEBVTT\n\n01:30.500 --> 02:00.000\nHello.\n"

    payload = webvtt.parse_webvtt(text=text, source="clip.vtt")

    assert payload["segments"][0]["start"] == 90.5
    assert payload["segments"][0]["end"] == 120.0


def test_parse_webvtt__reads_an_hour_long_timestamp() -> None:
    text = "WEBVTT\n\n01:00:00.000 --> 01:00:01.000\nHello.\n"

    payload = webvtt.parse_webvtt(text=text, source="clip.vtt")

    assert payload["segments"][0]["start"] == 3600.0


def test_parse_webvtt__ignores_cue_settings() -> None:
    text = "WEBVTT\n\n00:00:00.000 --> 00:00:01.000 align:start position:10%\nHello.\n"

    payload = webvtt.parse_webvtt(text=text, source="clip.vtt")

    assert payload["segments"] == [{"text": "Hello.", "start": 0.0, "end": 1.0}]


def test_parse_webvtt__strips_cue_markup() -> None:
    text = (
        "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\n"
        "<v Cook>I am <b>folding</b> the <00:00:00.500>dough.\n"
    )

    payload = webvtt.parse_webvtt(text=text, source="clip.vtt")

    assert payload["segments"][0]["text"] == "I am folding the dough."


def test_parse_webvtt__joins_a_multiline_cue() -> None:
    text = "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nI pick up\nthe pan.\n"

    payload = webvtt.parse_webvtt(text=text, source="clip.vtt")

    assert payload["segments"][0]["text"] == "I pick up the pan."


@pytest.mark.parametrize("block", ["NOTE a comment\nspanning two lines", "STYLE\n::cue { }"])
def test_parse_webvtt__skips_non_cue_blocks(block: str) -> None:
    text = f"WEBVTT\n\n{block}\n\n00:00:00.000 --> 00:00:01.000\nHello.\n"

    payload = webvtt.parse_webvtt(text=text, source="clip.vtt")

    assert payload["segments"] == [{"text": "Hello.", "start": 0.0, "end": 1.0}]


def test_parse_webvtt__drops_a_cue_with_no_text() -> None:
    text = (
        "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\n<v Cook>\n\n00:00:01.000 --> 00:00:02.000\nHi.\n"
    )

    payload = webvtt.parse_webvtt(text=text, source="clip.vtt")

    assert payload["segments"] == [{"text": "Hi.", "start": 1.0, "end": 2.0}]


def test_parse_webvtt__reads_a_language_header() -> None:
    text = "WEBVTT\nLanguage: en\n\n00:00:00.000 --> 00:00:01.000\nHello.\n"

    payload = webvtt.parse_webvtt(text=text, source="clip.vtt")

    assert payload["language"] == "en"


def test_parse_webvtt__language_is_none_without_a_header() -> None:
    # Nothing in the format requires a language, so the transcript travels without
    # one rather than with a guess.
    text = "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nHello.\n"

    payload = webvtt.parse_webvtt(text=text, source="clip.vtt")

    assert payload["language"] is None


def test_parse_webvtt__accepts_a_byte_order_mark() -> None:
    text = "﻿WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nHello.\n"

    payload = webvtt.parse_webvtt(text=text, source="clip.vtt")

    assert payload["segments"][0]["text"] == "Hello."


def test_parse_webvtt__an_empty_file_has_no_segments() -> None:
    payload = webvtt.parse_webvtt(text="WEBVTT\n", source="clip.vtt")

    assert payload["segments"] == []
    assert payload["text"] == ""


def test_parse_webvtt__rejects_a_file_without_the_signature() -> None:
    with pytest.raises(ValueError, match="WEBVTT signature"):
        webvtt.parse_webvtt(text='{"text": "Hi."}', source="clip.vtt")


def test_parse_webvtt__rejects_a_cue_without_a_timing() -> None:
    text = "WEBVTT\n\nan orphan line\nand another\n"

    with pytest.raises(ValueError, match="no timing line"):
        webvtt.parse_webvtt(text=text, source="clip.vtt")


def test_parse_webvtt__rejects_a_header_that_swallows_the_first_cue() -> None:
    # Without the blank line the format requires, the first cue would be read as
    # header metadata and silently dropped.
    text = "WEBVTT\n00:00:00.000 --> 00:00:01.000\nHello.\n"

    with pytest.raises(ValueError, match="blank line"):
        webvtt.parse_webvtt(text=text, source="clip.vtt")
