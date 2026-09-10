"""Segment a full egocentric transcript into chapters with one language-model call.

This replaces the per-chunk narration classifier for the throughput-critical path: one
request per video returns ordered chapters, from which task/environment share and repetition
are derived deterministically. Chapters are anchored by a verbatim opening phrase so word
timestamps can be re-attached later without sending them to the model.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

import httpx

from lightly_studio.dataset.narration_classification import (
    LABELS,
    LIKELY_PASS_PERCENTAGE,
    MANUAL_REVIEW_MIN_PERCENTAGE,
    OFFICIAL_REQUIREMENT_PERCENTAGE,
    NarrationLabel,
    NarrationLlmProvider,
    NarrationQaStatus,
)

CHAPTER_PROMPT_VERSION = "chapters-v1"
DEFAULT_MAX_OUTPUT_TOKENS = 2048
DEFAULT_TIMEOUT_S = 180.0
DEFAULT_MAX_RETRIES = 1
DEFAULT_MAX_WORKERS = 6
DEFAULT_REPETITION_MAX_RATIO = 0.5
MIN_CHAPTERS_FOR_REPETITION = 2

TASK_LABELS = frozenset({"TASK", "BOTH"})
ENVIRONMENT_LABELS = frozenset({"ENVIRONMENT", "BOTH"})
QUALIFYING_LABELS = frozenset({"TASK", "ENVIRONMENT", "BOTH"})

_DESC_STOPWORDS = frozenset(
    {"a", "an", "the", "and", "or", "of", "on", "in", "to", "with", "at", "for", "up", "down"}
)
_ANCHOR_NORMALIZE_PATTERN = re.compile(r"[^\w\s]", flags=re.UNICODE)
_WHITESPACE_PATTERN = re.compile(r"\s+", flags=re.UNICODE)
_THINK_PATTERN = re.compile(r"<think>.*?</think>", flags=re.DOTALL | re.IGNORECASE)

_MAX_CHAPTERS = 12

_SYSTEM_PROMPT = f"""You split the full narration transcript of one egocentric task video into \
sequential chapters. A chapter is a long contiguous stretch of narration about ONE activity.

Rules:
- Return AT MOST {_MAX_CHAPTERS} chapters. Prefer fewer, larger chapters.
- Never emit one chapter per sentence. A new chapter starts only when the activity clearly \
changes. Consecutive sentences about the same activity belong to the SAME chapter.
- Cover the whole transcript in order with non-overlapping chapters.

For every chapter return:
- anchor: copy the FIRST 3 to 5 words of the chapter verbatim from the transcript, exactly as \
written. Do not paraphrase; this locates the chapter in the text.
- label: exactly one of TASK, ENVIRONMENT, BOTH, OTHER.
  - TASK: describes an action, procedure, goal, tool use, or manual step.
  - ENVIRONMENT: describes visible objects, layout, state, location, or surroundings.
  - BOTH: meaningful task and environment information together.
  - OTHER: conversation, history, opinion, filler, or unrelated content.
- desc: 3 to 5 words naming the activity.

Return JSON only as {{"chapters": [{{"anchor": string, "label": string, "desc": string}}]}}.
/no_think"""


@dataclass(frozen=True)
class TranscriptChapter:
    """One chapter returned by the model.

    Attributes:
        anchor: Verbatim opening phrase used to locate the chapter in the transcript.
        label: Narration label describing the chapter content.
        desc: Short human-readable activity name.
    """

    anchor: str
    label: NarrationLabel
    desc: str


@dataclass(frozen=True)
class ChapterSummary:
    """Deterministic per-video summary derived from chapters.

    Attributes:
        chapters: The model chapters in transcript order.
        total_word_count: Words in the transcript used for weighting.
        label_word_percentages: Word-weighted share of each label.
        task_percentage: Word-weighted share of TASK and BOTH chapters.
        environment_percentage: Word-weighted share of ENVIRONMENT and BOTH chapters.
        qualifying_percentage: Word-weighted share of TASK, ENVIRONMENT, and BOTH chapters.
        repetition_ratio: Word share of the single most repeated activity.
        dominant_activity: The activity name behind ``repetition_ratio``.
        is_repetitive: Whether one activity dominates the transcript.
        requirement_pass: Whether ``qualifying_percentage`` meets the contractual threshold.
        status: Pass/review/fail bucket based on ``qualifying_percentage``.
    """

    chapters: tuple[TranscriptChapter, ...]
    total_word_count: int
    label_word_percentages: dict[NarrationLabel, float]
    task_percentage: float
    environment_percentage: float
    qualifying_percentage: float
    repetition_ratio: float
    dominant_activity: str
    is_repetitive: bool
    requirement_pass: bool
    status: NarrationQaStatus


@dataclass(frozen=True)
class ChapterClassifierSettings:
    """Connection settings for the chapter classifier.

    Attributes:
        base_url: Base URL of the Ollama or OpenAI-compatible server.
        model: Model name to request.
        provider: Which wire protocol to use.
        api_key: Optional bearer token for OpenAI-compatible servers.
        timeout_s: Per-request timeout in seconds.
        max_retries: Extra attempts after the first failure.
        max_output_tokens: Generation cap for the chapters response.
    """

    base_url: str
    model: str
    provider: NarrationLlmProvider = "ollama"
    api_key: str | None = None
    timeout_s: float = DEFAULT_TIMEOUT_S
    max_retries: int = DEFAULT_MAX_RETRIES
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS


class ChapterClassifier:
    """Split full transcripts into chapters through a chat-completions endpoint."""

    def __init__(
        self,
        settings: ChapterClassifierSettings,
        client: httpx.Client | None = None,
    ) -> None:
        """Initialize the client from explicit connection settings.

        Args:
            settings: Connection and generation settings.
            client: Optional shared HTTP client; one is created when omitted.

        Raises:
            ValueError: If ``max_output_tokens`` is not positive.
        """
        if settings.max_output_tokens <= 0:
            raise ValueError("Chapter classifier maximum output tokens must be positive.")
        self._provider = settings.provider
        endpoint_path = "/api/chat" if settings.provider == "ollama" else "/chat/completions"
        self._endpoint = f"{settings.base_url.rstrip('/')}{endpoint_path}"
        self.model = settings.model
        self._timeout_s = settings.timeout_s
        self._max_retries = settings.max_retries
        self._max_output_tokens = settings.max_output_tokens
        self._client = client or httpx.Client()
        self._headers = {"Content-Type": "application/json"}
        if settings.api_key:
            self._headers["Authorization"] = f"Bearer {settings.api_key}"

    def classify_transcript(self, text: str) -> list[TranscriptChapter]:
        """Return the chapters for one full transcript.

        Args:
            text: The complete transcript narration text.

        Returns:
            Chapters in transcript order; empty when the transcript has no words.

        Raises:
            ValueError: If the model response cannot be parsed after all retries.
        """
        if not text.strip():
            return []
        payload = _build_request_payload(
            model=self.model,
            text=text,
            max_output_tokens=self._max_output_tokens,
            provider=self._provider,
        )
        last_error: Exception | None = None
        for _ in range(self._max_retries + 1):
            try:
                response = self._client.post(
                    self._endpoint,
                    headers=self._headers,
                    json=payload,
                    timeout=self._timeout_s,
                )
                response.raise_for_status()
                return _parse_response(payload=response.json(), provider=self._provider)
            except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
                last_error = error
        raise ValueError(f"Chapter classification failed: {last_error}") from last_error

    def classify_many(
        self,
        texts_by_key: Sequence[tuple[str, str]],
        max_workers: int = DEFAULT_MAX_WORKERS,
        on_complete: Callable[[str], None] | None = None,
        on_error: Callable[[str, Exception], None] | None = None,
    ) -> dict[str, list[TranscriptChapter]]:
        """Classify many transcripts concurrently to saturate a batching server.

        A failure on one transcript does not abort the batch; failed keys are omitted from the
        result and reported through ``on_error``.

        Args:
            texts_by_key: Pairs of ``(key, transcript_text)``.
            max_workers: Number of requests to keep in flight at once.
            on_complete: Optional callback invoked with each key as it finishes.
            on_error: Optional callback invoked with the key and error when a transcript fails.

        Returns:
            Mapping from key to that transcript's chapters. Keys that fail are omitted.
        """
        results: dict[str, list[TranscriptChapter]] = {}
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            future_to_key = {
                pool.submit(self.classify_transcript, text): key for key, text in texts_by_key
            }
            for future in as_completed(future_to_key):
                key = future_to_key[future]
                try:
                    results[key] = future.result()
                except Exception as error:  # Isolate one bad transcript from the whole batch.
                    if on_error is not None:
                        on_error(key, error)
                finally:
                    if on_complete is not None:
                        on_complete(key)
        return results


def summarize_chapters(
    text: str,
    chapters: Sequence[TranscriptChapter],
    repetition_max_ratio: float = DEFAULT_REPETITION_MAX_RATIO,
) -> ChapterSummary:
    """Derive word-weighted label shares and a repetition flag from chapters.

    Words are attributed to chapters by locating each anchor in the transcript and splitting the
    text at those positions, so the percentages are word-weighted like the legacy per-chunk metric.

    Args:
        text: The complete transcript narration text.
        chapters: Model chapters in transcript order.
        repetition_max_ratio: Dominant-activity word share at or above which the video is
            flagged as repetitive.

    Returns:
        The per-video chapter summary.
    """
    chapter_word_counts = _assign_word_counts(text=text, chapters=chapters)
    total_word_count = sum(chapter_word_counts)
    label_word_counts: dict[NarrationLabel, int] = dict.fromkeys(LABELS, 0)
    for chapter, words in zip(chapters, chapter_word_counts):
        label_word_counts[chapter.label] += words

    dominant_activity, dominant_words = _dominant_theme(
        chapters=chapters,
        chapter_word_counts=chapter_word_counts,
    )
    repetition_ratio = _percentage(numerator=dominant_words, denominator=total_word_count) / 100.0
    qualifying_percentage = _label_percentage(
        label_word_counts=label_word_counts,
        labels=QUALIFYING_LABELS,
        total_word_count=total_word_count,
    )
    return ChapterSummary(
        chapters=tuple(chapters),
        total_word_count=total_word_count,
        label_word_percentages={
            label: _percentage(numerator=count, denominator=total_word_count)
            for label, count in label_word_counts.items()
        },
        task_percentage=_label_percentage(
            label_word_counts=label_word_counts,
            labels=TASK_LABELS,
            total_word_count=total_word_count,
        ),
        environment_percentage=_label_percentage(
            label_word_counts=label_word_counts,
            labels=ENVIRONMENT_LABELS,
            total_word_count=total_word_count,
        ),
        qualifying_percentage=qualifying_percentage,
        repetition_ratio=repetition_ratio,
        dominant_activity=dominant_activity,
        is_repetitive=(
            len(chapters) >= MIN_CHAPTERS_FOR_REPETITION
            and repetition_ratio >= repetition_max_ratio
        ),
        requirement_pass=qualifying_percentage >= OFFICIAL_REQUIREMENT_PERCENTAGE,
        status=_get_status(qualifying_percentage=qualifying_percentage),
    )


def summary_to_dict(summary: ChapterSummary) -> dict[str, Any]:
    """Convert a summary to a JSON-serializable record."""
    return {
        "prompt_version": CHAPTER_PROMPT_VERSION,
        "total_word_count": summary.total_word_count,
        "task_percentage": summary.task_percentage,
        "environment_percentage": summary.environment_percentage,
        "qualifying_percentage": summary.qualifying_percentage,
        "requirement_pass": summary.requirement_pass,
        "status": summary.status,
        "repetition_ratio": summary.repetition_ratio,
        "dominant_activity": summary.dominant_activity,
        "is_repetitive": summary.is_repetitive,
        "label_word_percentages": summary.label_word_percentages,
        "chapters": [
            {"anchor": chapter.anchor, "label": chapter.label, "desc": chapter.desc}
            for chapter in summary.chapters
        ],
    }


def _assign_word_counts(
    text: str,
    chapters: Sequence[TranscriptChapter],
) -> list[int]:
    normalized_text = _normalize_text(text)
    total_words = len(normalized_text.split())
    # Locate each anchor in order and convert its position to a running word offset. Spans between
    # consecutive offsets give each chapter its word count; the last chapter runs to the end.
    word_offsets: list[int] = []
    search_start = 0
    for index, chapter in enumerate(chapters):
        position = _find_anchor(
            normalized_text=normalized_text,
            anchor=chapter.anchor,
            search_start=search_start,
        )
        if position is None or index == 0:
            position = search_start
        word_offsets.append(_word_count_before(normalized_text=normalized_text, position=position))
        search_start = position
    word_offsets = [0, *word_offsets[1:]] if word_offsets else word_offsets
    return [
        max((word_offsets[index + 1] if index + 1 < len(word_offsets) else total_words) - offset, 0)
        for index, offset in enumerate(word_offsets)
    ]


def _normalize_text(text: str) -> str:
    collapsed = _ANCHOR_NORMALIZE_PATTERN.sub(" ", text.lower())
    return _WHITESPACE_PATTERN.sub(" ", collapsed)


def _normalize_anchor(anchor: str) -> str:
    return _normalize_text(anchor).strip()


def _find_anchor(normalized_text: str, anchor: str, search_start: int) -> int | None:
    normalized_anchor = _normalize_anchor(anchor)
    if not normalized_anchor:
        return None
    position = normalized_text.find(normalized_anchor, search_start)
    if position >= 0:
        return position
    return normalized_text.find(normalized_anchor)


def _word_count_before(normalized_text: str, position: int) -> int:
    return len(normalized_text[:position].split())


def _dominant_theme(
    chapters: Sequence[TranscriptChapter],
    chapter_word_counts: Sequence[int],
) -> tuple[str, int]:
    # Weight each significant description word by the transcript words in its chapters, so a video
    # that keeps returning to one activity (e.g. many "sweep ..." chapters) reads as repetitive
    # even when the model phrases each chapter differently.
    theme_word_counts: dict[str, int] = {}
    for chapter, words in zip(chapters, chapter_word_counts):
        for token in set(_significant_tokens(chapter.desc)):
            theme_word_counts[token] = theme_word_counts.get(token, 0) + words
    if not theme_word_counts:
        return "", 0
    theme = max(theme_word_counts, key=lambda key: theme_word_counts[key])
    return theme, theme_word_counts[theme]


def _significant_tokens(desc: str) -> list[str]:
    normalized = _normalize_text(desc)
    return [token for token in normalized.split() if token not in _DESC_STOPWORDS]


def _label_percentage(
    label_word_counts: dict[NarrationLabel, int],
    labels: frozenset[str],
    total_word_count: int,
) -> float:
    numerator = sum(count for label, count in label_word_counts.items() if label in labels)
    return _percentage(numerator=numerator, denominator=total_word_count)


def _build_request_payload(
    model: str,
    text: str,
    max_output_tokens: int,
    provider: NarrationLlmProvider,
) -> dict[str, Any]:
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"{json.dumps({'transcript': text})}\n/no_think",
        },
    ]
    if provider == "ollama":
        return {
            "model": model,
            "messages": messages,
            "stream": False,
            "think": False,
            "format": _chapters_json_schema(),
            "options": {
                "temperature": 0,
                "num_predict": max_output_tokens,
            },
        }
    return {
        "model": model,
        "temperature": 0,
        "max_tokens": max_output_tokens,
        "stream": False,
        "response_format": {"type": "json_object"},
        "messages": messages,
    }


def _chapters_json_schema() -> dict[str, Any]:
    chapter_schema = {
        "type": "object",
        "properties": {
            "anchor": {"type": "string"},
            "label": {"type": "string", "enum": list(LABELS)},
            "desc": {"type": "string"},
        },
        "required": ["anchor", "label", "desc"],
    }
    return {
        "type": "object",
        "properties": {
            "chapters": {
                "type": "array",
                "items": chapter_schema,
                "maxItems": _MAX_CHAPTERS,
            }
        },
        "required": ["chapters"],
    }


def _parse_response(payload: Any, provider: NarrationLlmProvider) -> list[TranscriptChapter]:
    content = (
        payload["message"]["content"]
        if provider == "ollama"
        else payload["choices"][0]["message"]["content"]
    )
    if not isinstance(content, str):
        raise ValueError("Model response content must be a string.")
    parsed = json.loads(_extract_json_object(content=content))
    raw_chapters = parsed.get("chapters") if isinstance(parsed, dict) else None
    if not isinstance(raw_chapters, list):
        raise ValueError(f"Model response must contain a chapters list, got: {parsed!r}.")
    return [_parse_chapter(raw_chapter=raw_chapter) for raw_chapter in raw_chapters]


def _parse_chapter(raw_chapter: Any) -> TranscriptChapter:
    if not isinstance(raw_chapter, dict):
        raise ValueError("Every chapter must be an object.")
    anchor = raw_chapter.get("anchor")
    label = raw_chapter.get("label")
    desc = raw_chapter.get("desc")
    if not isinstance(anchor, str) or not anchor.strip():
        raise ValueError("Every chapter must have a nonempty string anchor.")
    if label not in LABELS:
        raise ValueError(f"Unknown chapter label: {label!r}.")
    if not isinstance(desc, str) or not desc.strip():
        raise ValueError("Every chapter must have a nonempty string desc.")
    return TranscriptChapter(anchor=anchor.strip(), label=label, desc=desc.strip())


def _extract_json_object(content: str) -> str:
    without_thinking = _THINK_PATTERN.sub("", content).strip()
    start = without_thinking.find("{")
    end = without_thinking.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Model response did not contain a JSON object.")
    return without_thinking[start : end + 1]


def _percentage(numerator: int, denominator: int) -> float:
    return numerator * 100.0 / denominator if denominator > 0 else 0.0


def _get_status(qualifying_percentage: float) -> NarrationQaStatus:
    if qualifying_percentage >= LIKELY_PASS_PERCENTAGE:
        return "likely_pass"
    if qualifying_percentage >= MANUAL_REVIEW_MIN_PERCENTAGE:
        return "manual_review"
    return "likely_fail"
