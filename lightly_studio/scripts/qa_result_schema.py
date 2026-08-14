"""Build the human-readable, self-describing QA result payload."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from lightly_studio.dataset import (
    caption_repetition,
    caption_segment_matching,
    egocentric_qa,
    narration_classification,
    video_quality,
)

RESULT_SCHEMA_VERSION = 2
QA_POLICY_VERSION = 1

CheckSeverity = Literal["blocking", "review"]

_TECHNICAL_FIELDS = {
    "qa_resolution_pass": "resolution_passed",
    "qa_duration_pass": "duration_passed",
    "qa_orientation": "orientation",
    "qa_media_format": "media_format",
    "qa_preferred_format": "preferred_format",
    "qa_is_english": "is_english",
}
_AUDIO_FIELDS = {
    "qa_has_audio": "has_audio",
    "qa_has_narration": "has_narration",
    "qa_transcript_timestamps_valid": "transcript_timestamps_valid",
    "whisper_language": "language",
    "whisper_language_probability": "language_probability",
    "whisper_word_count": "word_count",
    "whisper_words_per_minute": "words_per_minute",
    "whisper_wpm_pass": "words_per_minute_passed",
    "whisper_caption_count": "caption_count",
    "whisper_caption_unit": "caption_unit",
    "whisper_speech_duration_s": "speech_duration_s",
    "whisper_silence_duration_s": "silence_duration_s",
    "whisper_silence_ratio": "silence_ratio",
    "whisper_silence_count": "silence_count",
}
_VISUAL_FIELDS = {
    video_quality.BLUR_SCORE_KEY: "blur_score",
    video_quality.BRIGHTNESS_MEAN_KEY: "brightness_mean",
    video_quality.UNDEREXPOSURE_RATIO_KEY: "underexposure_ratio",
    video_quality.OVEREXPOSURE_RATIO_KEY: "overexposure_ratio",
    video_quality.LIGHTING_SCORE_KEY: "lighting_score",
    video_quality.MOTION_SCORE_KEY: "motion_score",
}
_PIPELINE_FIELDS = {
    "qa_pipeline_complete": "complete",
    "qa_deterministic_pass": "deterministic_passed",
}
_VERDICT_FIELDS = {
    "automated_qa_status",
    "automated_qa_failure_count",
    "automated_qa_failures",
    "automated_qa_review_issue_count",
    "automated_qa_review_issues",
    "automated_qa_issue_count",
    "automated_qa_issues",
    "expected_quality_label",
}
_SOURCE_FIELDS = {
    "qa_source_bucket",
    "qa_source_prefix",
    "qa_source_stem",
    "qa_source_video_url",
    "qa_source_files",
}


def build_verdict(metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Build the concise human-triage verdict."""
    failures = _as_issue_list(metadata.get("automated_qa_failures"))
    stored_review_issues = _as_issue_list(metadata.get("automated_qa_review_issues"))
    review_issues = [issue for issue in stored_review_issues if issue != "narration_near_threshold"]
    issues = [*failures, *review_issues]
    status = _verdict_status(
        stored_status=metadata.get("automated_qa_status"),
        failures=failures,
        review_issues=review_issues,
        stored_review_issues=stored_review_issues,
    )
    return {
        "status": status,
        "expected_quality_label": metadata.get("expected_quality_label"),
        "failures": failures,
        "failure_count": len(failures),
        "review_issues": review_issues,
        "review_issue_count": len(review_issues),
        "issues": issues,
        "issue_count": len(issues),
    }


def build_checks(
    metadata: Mapping[str, Any],
    *,
    width: int,
    height: int,
    duration_s: float | None,
) -> dict[str, dict[str, Any]]:
    """Build threshold-bearing checks from raw video and metadata values."""
    qualifying_percentage = _number(metadata.get("narration_qualifying_percentage"))
    return {
        "resolution": _check(
            value={
                "width": width,
                "height": height,
                "short_edge": min(width, height),
                "long_edge": max(width, height),
            },
            passed=_boolean(metadata.get("qa_resolution_pass")),
            severity="blocking",
            rule={
                "short_edge_min": egocentric_qa.MIN_RESOLUTION_SHORT_EDGE_PX,
                "long_edge_min": egocentric_qa.MIN_RESOLUTION_LONG_EDGE_PX,
            },
            issue="low_resolution",
        ),
        "duration": _check(
            value=duration_s,
            passed=_boolean(metadata.get("qa_duration_pass")),
            severity="blocking",
            rule={
                "min": egocentric_qa.MIN_VIDEO_DURATION_S,
                "max": egocentric_qa.MAX_VIDEO_DURATION_S,
                "inclusive": True,
            },
            issue="invalid_duration",
        ),
        "audio_stream": _boolean_check(
            value=metadata.get("qa_has_audio"),
            severity="blocking",
            issue="no_audio_stream",
        ),
        "narration_present": _boolean_check(
            value=metadata.get("qa_has_narration"),
            severity="blocking",
            issue="no_narration",
        ),
        "narration_density": _check(
            value=_number(metadata.get("whisper_words_per_minute")),
            passed=_boolean(metadata.get("whisper_wpm_pass")),
            severity="blocking",
            rule={
                "operator": ">=",
                "threshold": egocentric_qa.MIN_NARRATION_WORDS_PER_MINUTE,
            },
            issue="low_narration_density",
        ),
        "transcript_timestamps": _boolean_check(
            value=metadata.get("qa_transcript_timestamps_valid"),
            severity="blocking",
            issue="invalid_transcript_timestamps",
        ),
        "narration_classification": _boolean_check(
            value=metadata.get("narration_classification_complete"),
            severity="blocking",
            issue="narration_classification_incomplete",
        ),
        "task_environment_narration": _check(
            value=qualifying_percentage,
            passed=(
                qualifying_percentage >= narration_classification.OFFICIAL_REQUIREMENT_PERCENTAGE
                if qualifying_percentage is not None
                else None
            ),
            severity="blocking",
            rule={
                "operator": ">=",
                "threshold": narration_classification.OFFICIAL_REQUIREMENT_PERCENTAGE,
                "unit": "percent",
            },
            issue="insufficient_task_environment_narration",
        ),
        "action_phrases": _minimum_check(
            value=metadata.get("whisper_caption_count"),
            threshold=egocentric_qa.MIN_NARRATION_CAPTION_COUNT,
            severity="review",
            issue="no_action_phrases",
        ),
        "blur": _minimum_check(
            value=metadata.get(video_quality.BLUR_SCORE_KEY),
            threshold=video_quality.DEFAULT_BLUR_SCORE_LOW_MAX,
            severity="review",
            issue="blurry",
        ),
        "lighting": _minimum_check(
            value=metadata.get(video_quality.LIGHTING_SCORE_KEY),
            threshold=video_quality.DEFAULT_LIGHTING_SCORE_LOW_MAX,
            severity="review",
            issue="poor_lighting",
        ),
        "motion": _minimum_check(
            value=metadata.get(video_quality.MOTION_SCORE_KEY),
            threshold=video_quality.DEFAULT_MOTION_SCORE_LOW_MAX,
            severity="review",
            issue="static_camera",
        ),
        "caption_match": _minimum_check(
            value=metadata.get(caption_segment_matching.MIN_CAPTION_SEGMENT_MATCH_SCORE_KEY),
            threshold=caption_segment_matching.DEFAULT_MIN_CAPTION_SEGMENT_MATCH_SCORE,
            severity="review",
            issue="low_caption_match",
        ),
        "caption_repetition": _maximum_check(
            value=metadata.get(caption_repetition.REPEATED_CAPTION_GROUP_COUNT_KEY),
            threshold=0,
            severity="review",
            issue="repeated_actions",
            rule_details={
                "detection_similarity_min": caption_repetition.DEFAULT_SIMILARITY_THRESHOLD
            },
        ),
    }


def build_metrics(metadata: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Group every persisted metadata field into a stable readable namespace."""
    consumed = set(_VERDICT_FIELDS) | set(_SOURCE_FIELDS)
    technical = _mapped_values(metadata=metadata, fields=_TECHNICAL_FIELDS, consumed=consumed)
    audio = _mapped_values(metadata=metadata, fields=_AUDIO_FIELDS, consumed=consumed)
    visual = _mapped_values(metadata=metadata, fields=_VISUAL_FIELDS, consumed=consumed)
    pipeline = _mapped_values(metadata=metadata, fields=_PIPELINE_FIELDS, consumed=consumed)
    narration = _prefixed_values(metadata=metadata, prefix="narration_", consumed=consumed)
    diagnostics = _diagnostic_values(metadata=metadata, consumed=consumed)
    other = {key: value for key, value in metadata.items() if key not in consumed}
    return {
        "technical": technical,
        "audio": audio,
        "narration": narration,
        "visual": visual,
        "diagnostics": diagnostics,
        "pipeline": pipeline,
        "other": other,
    }


def _check(
    *,
    value: Any,
    passed: bool | None,
    severity: CheckSeverity,
    rule: Mapping[str, Any],
    issue: str,
) -> dict[str, Any]:
    status = "not_run" if passed is None else ("pass" if passed else "fail")
    return {
        "status": status,
        "severity": severity,
        "value": value,
        "rule": dict(rule),
        "issue_on_failure": issue,
    }


def _verdict_status(
    stored_status: Any,
    failures: list[str],
    review_issues: list[str],
    stored_review_issues: list[str],
) -> str | None:
    if failures:
        return "fail"
    if review_issues:
        return "review"
    if stored_review_issues == ["narration_near_threshold"]:
        return "pass"
    if stored_status in {"pass", "review", "fail"}:
        return str(stored_status)
    return None


def _boolean_check(value: Any, severity: CheckSeverity, issue: str) -> dict[str, Any]:
    boolean_value = _boolean(value)
    return _check(
        value=boolean_value,
        passed=boolean_value,
        severity=severity,
        rule={"expected": True},
        issue=issue,
    )


def _minimum_check(
    value: Any,
    threshold: float,
    severity: CheckSeverity,
    issue: str,
) -> dict[str, Any]:
    numeric_value = _number(value)
    return _check(
        value=numeric_value,
        passed=numeric_value >= threshold if numeric_value is not None else None,
        severity=severity,
        rule={"operator": ">=", "threshold": threshold},
        issue=issue,
    )


def _maximum_check(
    value: Any,
    threshold: float,
    severity: CheckSeverity,
    issue: str,
    rule_details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    numeric_value = _number(value)
    rule = {"operator": "<=", "threshold": threshold, **(rule_details or {})}
    return _check(
        value=numeric_value,
        passed=numeric_value <= threshold if numeric_value is not None else None,
        severity=severity,
        rule=rule,
        issue=issue,
    )


def _mapped_values(
    metadata: Mapping[str, Any],
    fields: Mapping[str, str],
    consumed: set[str],
) -> dict[str, Any]:
    values = {}
    for source_key, result_key in fields.items():
        if source_key in metadata:
            values[result_key] = metadata[source_key]
            consumed.add(source_key)
    return values


def _prefixed_values(
    metadata: Mapping[str, Any],
    prefix: str,
    consumed: set[str],
) -> dict[str, Any]:
    values = {}
    for key, value in metadata.items():
        if key.startswith(prefix):
            values[key.removeprefix(prefix)] = value
            consumed.add(key)
    return values


def _diagnostic_values(metadata: Mapping[str, Any], consumed: set[str]) -> dict[str, Any]:
    prefixes = ("caption_segment_", "min_caption_segment_", "avg_caption_segment_", "repeated_")
    values = {}
    for key, value in metadata.items():
        if key.startswith(prefixes):
            values[key] = value
            consumed.add(key)
    return values


def _as_issue_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [issue.strip() for issue in value.split(",") if issue.strip()]
    if isinstance(value, (list, tuple)):
        return [str(issue) for issue in value]
    return []


def _boolean(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _number(value: Any) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if isinstance(value, float) else int(value)
