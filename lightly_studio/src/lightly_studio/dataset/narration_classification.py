"""Classify timed narration chunks with an OpenAI-compatible language model."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

import httpx
from tqdm import tqdm

NarrationLabel = Literal["TASK", "ENVIRONMENT", "BOTH", "OTHER"]
NarrationQaStatus = Literal["likely_pass", "manual_review", "likely_fail"]
NarrationLlmProvider = Literal["ollama", "openai"]

LABELS: tuple[NarrationLabel, ...] = ("TASK", "ENVIRONMENT", "BOTH", "OTHER")
QUALIFYING_LABELS = frozenset({"TASK", "ENVIRONMENT", "BOTH"})
PROMPT_VERSION = "narration-v1"
OFFICIAL_REQUIREMENT_PERCENTAGE = 70.0
LIKELY_PASS_PERCENTAGE = 80.0
MANUAL_REVIEW_MIN_PERCENTAGE = 60.0
DEFAULT_BATCH_SIZE = 8
DEFAULT_TIMEOUT_S = 90.0
DEFAULT_MAX_RETRIES = 1
DEFAULT_MAX_OUTPUT_TOKENS = 1024

_WORD_PATTERN = re.compile(r"\b[\w'-]+\b", flags=re.UNICODE)
_THINK_PATTERN = re.compile(r"<think>.*?</think>", flags=re.DOTALL | re.IGNORECASE)

_SYSTEM_PROMPT = """You classify the TARGET narration from egocentric task videos.
Use exactly one label:
- TASK: describes an action, procedure, goal, tool use, or manual step.
- ENVIRONMENT: describes visible objects, layout, state, location, or surroundings.
- BOTH: contains meaningful task and environment information.
- OTHER: conversation, history, opinion, filler, or unrelated content.

PREVIOUS and NEXT are context only. Classify only TARGET. Mark context_dependent when TARGET
cannot be understood confidently without context. Mark asr_unclear for likely transcription errors.
Return JSON only as {"results": [{"id": string, "label": string,
"context_dependent": boolean, "asr_unclear": boolean, "reason": string}]}.
Return exactly one result for every input id and no extra ids. Keep each reason under 12 words.
/no_think"""


@dataclass(frozen=True)
class NarrationChunk:
    """A target narration chunk plus optional neighboring context."""

    id: str
    text: str
    previous_text: str | None = None
    next_text: str | None = None


@dataclass(frozen=True)
class NarrationClassification:
    """Validated model classification for one narration chunk."""

    chunk_id: str
    label: NarrationLabel
    context_dependent: bool
    asr_unclear: bool
    reason: str

    @property
    def needs_review(self) -> bool:
        """Return whether the chunk has an uncertainty flag."""
        return self.context_dependent or self.asr_unclear


@dataclass(frozen=True)
class NarrationSummary:
    """Word-weighted classification summary for one video."""

    total_word_count: int
    qualifying_word_count: int
    qualifying_percentage: float
    label_word_counts: dict[NarrationLabel, int]
    label_word_percentages: dict[NarrationLabel, float]
    review_chunk_count: int
    requirement_pass: bool
    status: NarrationQaStatus


@dataclass(frozen=True)
class NarrationClassifierSettings:
    """Connection and batching settings for the narration classifier."""

    base_url: str
    model: str
    provider: NarrationLlmProvider = "ollama"
    api_key: str | None = None
    batch_size: int = DEFAULT_BATCH_SIZE
    timeout_s: float = DEFAULT_TIMEOUT_S
    max_retries: int = DEFAULT_MAX_RETRIES
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
    show_progress: bool = False


class OpenAICompatibleNarrationClassifier:
    """Classify chunks through an OpenAI-compatible chat completions endpoint."""

    def __init__(
        self,
        settings: NarrationClassifierSettings,
        client: httpx.Client | None = None,
    ) -> None:
        """Initialize the client from explicit connection settings."""
        if settings.batch_size <= 0:
            raise ValueError("Classification batch size must be positive.")
        if settings.max_output_tokens <= 0:
            raise ValueError("Classification maximum output tokens must be positive.")
        self._provider = settings.provider
        endpoint_path = "/api/chat" if settings.provider == "ollama" else "/chat/completions"
        self._endpoint = f"{settings.base_url.rstrip('/')}{endpoint_path}"
        self.model = settings.model
        self._batch_size = settings.batch_size
        self._timeout_s = settings.timeout_s
        self._max_retries = settings.max_retries
        self._max_output_tokens = settings.max_output_tokens
        self._show_progress = settings.show_progress
        self._client = client or httpx.Client()
        self._headers = {"Content-Type": "application/json"}
        if settings.api_key:
            self._headers["Authorization"] = f"Bearer {settings.api_key}"

    def classify(
        self,
        chunks: Sequence[NarrationChunk],
        on_batch_complete: Callable[[Sequence[NarrationClassification]], None] | None = None,
    ) -> list[NarrationClassification]:
        """Classify chunks in batches while preserving their input order.

        Args:
            chunks: Narration chunks to classify.
            on_batch_complete: Optional callback receiving each completed batch.

        Returns:
            Classifications in the same order as the input chunks.
        """
        classifications: list[NarrationClassification] = []
        starts = range(0, len(chunks), self._batch_size)
        progress = tqdm(
            starts,
            total=len(starts),
            desc="Classifying narration",
            unit="batch",
            disable=not self._show_progress,
        )
        for start in progress:
            batch = chunks[start : start + self._batch_size]
            batch_classifications = self._classify_batch(chunks=batch)
            classifications.extend(batch_classifications)
            if on_batch_complete is not None:
                on_batch_complete(batch_classifications)
        return classifications

    def probe(self) -> None:
        """Verify that the configured endpoint and model return valid output."""
        self.classify(chunks=[NarrationChunk(id="probe", text="I pick up the screwdriver.")])

    def _classify_batch(self, chunks: Sequence[NarrationChunk]) -> list[NarrationClassification]:
        request_chunks = [
            NarrationChunk(
                id=str(index),
                text=chunk.text,
                previous_text=chunk.previous_text,
                next_text=chunk.next_text,
            )
            for index, chunk in enumerate(chunks)
        ]
        payload = _build_request_payload(
            model=self.model,
            chunks=request_chunks,
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
                local_results = _parse_response(
                    payload=response.json(),
                    chunks=request_chunks,
                    provider=self._provider,
                )
                return [
                    NarrationClassification(
                        chunk_id=chunks[index].id,
                        label=result.label,
                        context_dependent=result.context_dependent,
                        asr_unclear=result.asr_unclear,
                        reason=result.reason,
                    )
                    for index, result in enumerate(local_results)
                ]
            except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
                last_error = error
        if len(chunks) > 1:
            midpoint = len(chunks) // 2
            return [
                *self._classify_batch(chunks=chunks[:midpoint]),
                *self._classify_batch(chunks=chunks[midpoint:]),
            ]
        raise ValueError(f"Narration classification failed: {last_error}") from last_error


def summarize_classifications(
    chunks: Sequence[NarrationChunk],
    classifications: Sequence[NarrationClassification],
) -> NarrationSummary:
    """Calculate the word-weighted per-video narration summary."""
    classification_by_id = _validate_classification_ids(
        chunks=chunks,
        classifications=classifications,
    )
    label_word_counts: dict[NarrationLabel, int] = dict.fromkeys(LABELS, 0)
    review_chunk_count = 0
    for chunk in chunks:
        classification = classification_by_id[chunk.id]
        label_word_counts[classification.label] += count_words(text=chunk.text)
        review_chunk_count += classification.needs_review

    total_word_count = sum(label_word_counts.values())
    qualifying_word_count = sum(
        word_count for label, word_count in label_word_counts.items() if label in QUALIFYING_LABELS
    )
    qualifying_percentage = _percentage(
        numerator=qualifying_word_count,
        denominator=total_word_count,
    )
    return NarrationSummary(
        total_word_count=total_word_count,
        qualifying_word_count=qualifying_word_count,
        qualifying_percentage=qualifying_percentage,
        label_word_counts=label_word_counts,
        label_word_percentages={
            label: _percentage(numerator=count, denominator=total_word_count)
            for label, count in label_word_counts.items()
        },
        review_chunk_count=review_chunk_count,
        requirement_pass=qualifying_percentage >= OFFICIAL_REQUIREMENT_PERCENTAGE,
        status=_get_status(qualifying_percentage=qualifying_percentage),
    )


def count_words(text: str) -> int:
    """Count words consistently for score weighting and display."""
    return len(_WORD_PATTERN.findall(text))


def get_text_hash(text: str, model: str) -> str:
    """Return the cache key for a chunk, model, and prompt version."""
    value = f"{PROMPT_VERSION}\0{model}\0{text}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def classification_metadata(
    classification: NarrationClassification,
    text: str,
    model: str,
) -> dict[str, Any]:
    """Convert a classification to caption metadata."""
    return {
        "narration_label": classification.label,
        "narration_context_dependent": classification.context_dependent,
        "narration_asr_unclear": classification.asr_unclear,
        "narration_reason": classification.reason,
        "narration_needs_review": classification.needs_review,
        "narration_model": model,
        "narration_prompt_version": PROMPT_VERSION,
        "narration_text_hash": get_text_hash(text=text, model=model),
        "narration_classification_stale": False,
    }


def classification_from_metadata(
    metadata: Mapping[str, Any] | None,
    chunk_id: str,
    text: str,
    model: str,
) -> NarrationClassification | None:
    """Load a valid, current classification from caption metadata."""
    if metadata is None or metadata.get("narration_classification_stale") is True:
        return None
    if metadata.get("narration_text_hash") != get_text_hash(text=text, model=model):
        return None
    label = _as_label(value=metadata.get("narration_label"))
    context_dependent = metadata.get("narration_context_dependent")
    asr_unclear = metadata.get("narration_asr_unclear")
    reason = metadata.get("narration_reason")
    if (
        label is None
        or not isinstance(context_dependent, bool)
        or not isinstance(asr_unclear, bool)
        or not isinstance(reason, str)
        or not reason
    ):
        return None
    return NarrationClassification(
        chunk_id=chunk_id,
        label=label,
        context_dependent=context_dependent,
        asr_unclear=asr_unclear,
        reason=reason,
    )


def summary_metadata(summary: NarrationSummary, model: str) -> dict[str, Any]:
    """Convert a completed summary to video metadata."""
    metadata: dict[str, Any] = {
        "narration_qualifying_percentage": summary.qualifying_percentage,
        "narration_qualifying_word_count": summary.qualifying_word_count,
        "narration_total_word_count": summary.total_word_count,
        "narration_review_chunk_count": summary.review_chunk_count,
        "narration_requirement_pass": summary.requirement_pass,
        "narration_qa_status": summary.status,
        "narration_classification_complete": True,
        "narration_classification_stale": False,
        "narration_model": model,
        "narration_prompt_version": PROMPT_VERSION,
    }
    for label in LABELS:
        metadata[f"narration_{label.lower()}_word_percentage"] = summary.label_word_percentages[
            label
        ]
    return metadata


def _build_request_payload(
    model: str,
    chunks: Sequence[NarrationChunk],
    max_output_tokens: int,
    provider: NarrationLlmProvider,
) -> dict[str, Any]:
    request_chunks = [
        {
            "id": chunk.id,
            "previous": chunk.previous_text,
            "target": chunk.text,
            "next": chunk.next_text,
        }
        for chunk in chunks
    ]
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"{json.dumps({'chunks': request_chunks})}\n/no_think",
        },
    ]
    if provider == "ollama":
        return {
            "model": model,
            "messages": messages,
            "stream": False,
            "think": False,
            "format": _result_json_schema(result_ids=[chunk.id for chunk in chunks]),
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


def _result_json_schema(result_ids: Sequence[str]) -> dict[str, Any]:
    result_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string", "enum": list(result_ids)},
            "label": {"type": "string", "enum": list(LABELS)},
            "context_dependent": {"type": "boolean"},
            "asr_unclear": {"type": "boolean"},
            "reason": {"type": "string"},
        },
        "required": ["id", "label", "context_dependent", "asr_unclear", "reason"],
    }
    return {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": result_schema,
                "minItems": len(result_ids),
                "maxItems": len(result_ids),
            }
        },
        "required": ["results"],
    }


def _parse_response(
    payload: Any,
    chunks: Sequence[NarrationChunk],
    provider: NarrationLlmProvider,
) -> list[NarrationClassification]:
    content = (
        payload["message"]["content"]
        if provider == "ollama"
        else payload["choices"][0]["message"]["content"]
    )
    if not isinstance(content, str):
        raise ValueError("Model response content must be a string.")
    parsed = json.loads(_extract_json_object(content=content))
    raw_results = parsed.get("results") if isinstance(parsed, dict) else None
    if not isinstance(raw_results, list):
        raise ValueError(f"Model response must contain a results list, got: {parsed!r}.")
    classifications = [_parse_result(raw_result=result) for result in raw_results]
    classification_by_id = _validate_classification_ids(
        chunks=chunks,
        classifications=classifications,
    )
    return [classification_by_id[chunk.id] for chunk in chunks]


def _extract_json_object(content: str) -> str:
    without_thinking = _THINK_PATTERN.sub("", content).strip()
    start = without_thinking.find("{")
    end = without_thinking.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Model response did not contain a JSON object.")
    return without_thinking[start : end + 1]


def _parse_result(raw_result: Any) -> NarrationClassification:
    if not isinstance(raw_result, dict):
        raise ValueError("Every model result must be an object.")
    chunk_id = raw_result.get("id")
    label = raw_result.get("label")
    context_dependent = raw_result.get("context_dependent")
    asr_unclear = raw_result.get("asr_unclear")
    reason = raw_result.get("reason")
    if not isinstance(chunk_id, str) or not chunk_id:
        raise ValueError("Every model result must have a nonempty string id.")
    if label not in LABELS:
        raise ValueError(f"Unknown narration label: {label!r}.")
    if not isinstance(context_dependent, bool) or not isinstance(asr_unclear, bool):
        raise ValueError("Model uncertainty flags must be booleans.")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("Every model result must include a reason.")
    return NarrationClassification(
        chunk_id=chunk_id,
        label=label,
        context_dependent=context_dependent,
        asr_unclear=asr_unclear,
        reason=reason.strip(),
    )


def _validate_classification_ids(
    chunks: Sequence[NarrationChunk],
    classifications: Sequence[NarrationClassification],
) -> dict[str, NarrationClassification]:
    chunk_ids = [chunk.id for chunk in chunks]
    classification_by_id = {
        classification.chunk_id: classification for classification in classifications
    }
    if len(classification_by_id) != len(classifications):
        raise ValueError("Model returned duplicate chunk ids.")
    if set(classification_by_id) != set(chunk_ids) or len(classifications) != len(chunks):
        raise ValueError("Model must return exactly one result for every input chunk.")
    return classification_by_id


def _percentage(numerator: int, denominator: int) -> float:
    return numerator * 100.0 / denominator if denominator > 0 else 0.0


def _get_status(qualifying_percentage: float) -> NarrationQaStatus:
    if qualifying_percentage >= LIKELY_PASS_PERCENTAGE:
        return "likely_pass"
    if qualifying_percentage >= MANUAL_REVIEW_MIN_PERCENTAGE:
        return "manual_review"
    return "likely_fail"


def _as_label(value: Any) -> NarrationLabel | None:
    if value == "TASK":
        return "TASK"
    if value == "ENVIRONMENT":
        return "ENVIRONMENT"
    if value == "BOTH":
        return "BOTH"
    if value == "OTHER":
        return "OTHER"
    return None
