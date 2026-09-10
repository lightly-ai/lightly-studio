"""Parse WebVTT subtitles into the payload shape the Whisper parser accepts.

WebVTT carries cue-level timings only, so each cue becomes one segment with no
``words`` list. Everything downstream already handles a wordless segment: the
narration chunker falls back to per-segment captions, and the word count falls back
to the joined text. The statistics that genuinely need per-word timings
(``speech_duration_s``, ``silences``) are left unset rather than synthesized, so a
delivered transcript never reports a fabricated measurement.
"""

from __future__ import annotations

import re
from typing import Any

VTT_SUFFIX = ".vtt"

_SIGNATURE = "WEBVTT"
# ``HH:MM:SS.mmm`` and the ``MM:SS.mmm`` short form, separated by ``-->`` and
# optionally followed by cue settings such as ``align:start position:10%``.
_TIMING = re.compile(
    r"^(?P<start>(?:\d+:)?\d{1,2}:\d{2}\.\d{1,3})\s*-->\s*"
    r"(?P<end>(?:\d+:)?\d{1,2}:\d{2}\.\d{1,3})(?:\s+\S.*)?$"
)
# Cue payload markup: voice and class spans, ``<b>``-style tags, inline timestamps.
_CUE_TAG = re.compile(r"</?[^>]*>")
# Blocks that carry no narration and may span several lines.
_IGNORED_BLOCK_PREFIXES = ("NOTE", "STYLE", "REGION")


def parse_webvtt(text: str, source: str = "transcript") -> dict[str, Any]:
    """Convert WebVTT into a payload ``parse_whisper_transcript`` understands.

    Args:
        text: Full contents of a ``.vtt`` file.
        source: Name used in error messages, normally the file path.

    Returns:
        A payload with the joined narration ``text``, an optional ``language`` read
        from the header, and one ``segments`` entry per cue. Segments carry no
        ``words`` key, because WebVTT has no per-word timings to put there.

    Raises:
        ValueError: If the signature is missing or a cue cannot be read.
    """
    header, cue_blocks = _split_blocks(text=text, source=source)
    segments = [
        segment
        for block in cue_blocks
        if (segment := _parse_cue(lines=block, source=source)) is not None
    ]
    return {
        "text": " ".join(segment["text"] for segment in segments),
        "language": _header_language(lines=header),
        "segments": segments,
    }


def _split_blocks(text: str, source: str) -> tuple[list[str], list[list[str]]]:
    """Split a VTT file into its header lines and one block per cue.

    Comment, style and region blocks are dropped here rather than downstream, so
    the caller only ever sees blocks that are meant to be cues.

    Returns:
        A tuple of (header lines, cue blocks).

    Raises:
        ValueError: If the signature is missing, or the blank line the format
            requires after the header is, which would silently swallow a cue.
    """
    # A leading byte-order mark is legal and would otherwise hide the signature.
    stripped = text.lstrip("﻿")
    if not stripped.startswith(_SIGNATURE):
        raise ValueError(f"Not a WebVTT file, missing the WEBVTT signature: '{source}'.")
    blocks = _group_nonempty_lines(text=stripped)
    header = blocks[0]
    if any(_TIMING.match(line) for line in header):
        raise ValueError(f"WebVTT header is not followed by a blank line: '{source}'.")
    cue_blocks = [block for block in blocks[1:] if not block[0].startswith(_IGNORED_BLOCK_PREFIXES)]
    return header, cue_blocks


def _group_nonempty_lines(text: str) -> list[list[str]]:
    """Group stripped lines into blocks separated by blank lines."""
    blocks: list[list[str]] = []
    current: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line:
            current.append(line)
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def _parse_cue(lines: list[str], source: str) -> dict[str, Any] | None:
    """Return one segment for a cue block, or None if the cue has no narration.

    Args:
        lines: Non-empty lines of a single cue, optionally led by a cue identifier.
        source: Name used in error messages.

    Returns:
        A segment with ``text``, ``start`` and ``end``, or None when the cue holds
        no text once its markup is stripped.

    Raises:
        ValueError: If no line of the block is a cue timing.
    """
    timed = ((index, _TIMING.match(line)) for index, line in enumerate(lines))
    found = next(((index, match) for index, match in timed if match is not None), None)
    if found is None:
        raise ValueError(f"WebVTT cue has no timing line: '{source}'.")
    # The only line a cue may carry before its timing is the cue identifier.
    timing_index, match = found
    payload = " ".join(_strip_tags(line) for line in lines[timing_index + 1 :])
    text = " ".join(payload.split())
    if not text:
        return None
    return {
        "text": text,
        "start": _parse_timestamp(value=match.group("start"), source=source),
        "end": _parse_timestamp(value=match.group("end"), source=source),
    }


def _parse_timestamp(value: str, source: str) -> float:
    """Convert a ``[HH:]MM:SS.mmm`` cue timestamp into seconds.

    Raises:
        ValueError: If a component is not a number.
    """
    try:
        numbers = [float(part) for part in value.split(":")]
    except ValueError as error:
        raise ValueError(f"Unreadable WebVTT timestamp '{value}': '{source}'.") from error
    seconds = 0.0
    for number in numbers:
        seconds = seconds * 60 + number
    return seconds


def _header_language(lines: list[str]) -> str | None:
    """Return the language from a ``Language:`` header line, if the file carries one.

    WebVTT allows arbitrary ``Key: Value`` metadata after the signature. Nothing
    requires a language, so the common case is None and the transcript travels
    without one rather than with a guess.
    """
    for line in lines:
        key, separator, value = line.partition(":")
        if separator and key.strip().lower() == "language" and value.strip():
            return value.strip()
    return None


def _strip_tags(line: str) -> str:
    return _CUE_TAG.sub(" ", line)
