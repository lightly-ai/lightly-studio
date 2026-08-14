from __future__ import annotations

import json

import httpx
import pytest

from lightly_studio.dataset import narration_classification
from lightly_studio.dataset.narration_classification import (
    NarrationChunk,
    NarrationClassification,
    NarrationClassifierSettings,
)


def test_openai_compatible_classifier() -> None:
    requests: list[dict[str, object]] = []

    def handle_request(request: httpx.Request) -> httpx.Response:
        request_body = json.loads(request.content)
        requests.append(request_body)
        user_content = request_body["messages"][1]["content"]
        request_chunk = json.loads(user_content.removesuffix("\n/no_think"))["chunks"][0]
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": (
                                "<think>ignored</think>"
                                f'{{"results": [{{"id": "{request_chunk["id"]}", '
                                '"label": "TASK", "context_dependent": false, '
                                '"asr_unclear": false, "reason": "Describes tightening."}]}'
                            )
                        }
                    }
                ]
            },
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handle_request))
    classifier = narration_classification.OpenAICompatibleNarrationClassifier(
        settings=NarrationClassifierSettings(
            base_url="http://localhost:11434/v1",
            model="qwen3:4b",
            provider="openai",
        ),
        client=http_client,
    )

    result = classifier.classify(chunks=[NarrationChunk(id="chunk-1", text="I tighten the screw.")])

    assert result == [
        NarrationClassification(
            chunk_id="chunk-1",
            label="TASK",
            context_dependent=False,
            asr_unclear=False,
            reason="Describes tightening.",
        )
    ]
    assert requests[0]["model"] == "qwen3:4b"
    assert requests[0]["temperature"] == 0
    assert requests[0]["max_tokens"] == 1024


def test_ollama_classifier_disables_thinking() -> None:
    requests: list[dict[str, object]] = []

    def handle_request(request: httpx.Request) -> httpx.Response:
        request_body = json.loads(request.content)
        requests.append(request_body)
        user_content = request_body["messages"][1]["content"]
        request_chunk = json.loads(user_content.removesuffix("\n/no_think"))["chunks"][0]
        return httpx.Response(
            200,
            json={
                "message": {
                    "content": (
                        f'{{"results": [{{"id": "{request_chunk["id"]}", "label": "TASK", '
                        '"context_dependent": false, "asr_unclear": false, '
                        '"reason": "Describes tightening."}]}'
                    )
                }
            },
        )

    classifier = narration_classification.OpenAICompatibleNarrationClassifier(
        settings=NarrationClassifierSettings(
            base_url="http://localhost:11434",
            model="qwen3:4b",
            provider="ollama",
        ),
        client=httpx.Client(transport=httpx.MockTransport(handle_request)),
    )

    result = classifier.classify(chunks=[NarrationChunk(id="chunk-1", text="I tighten the screw.")])

    assert result[0].label == "TASK"
    assert requests[0]["think"] is False
    assert requests[0]["format"]["required"] == ["results"]
    assert requests[0]["format"]["properties"]["results"]["items"]["properties"]["id"] == {
        "type": "string",
        "enum": ["0"],
    }
    assert requests[0]["options"] == {"temperature": 0, "num_predict": 1024}


def test_openai_compatible_classifier__reports_completed_batches() -> None:
    def handle_request(request: httpx.Request) -> httpx.Response:
        request_body = json.loads(request.content)
        user_content = request_body["messages"][1]["content"]
        user_message = json.loads(user_content.removesuffix("\n/no_think"))
        results = [
            {
                "id": chunk["id"],
                "label": "TASK",
                "context_dependent": False,
                "asr_unclear": False,
                "reason": "Describes an action.",
            }
            for chunk in user_message["chunks"]
        ]
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps({"results": results})}}]},
        )

    classifier = narration_classification.OpenAICompatibleNarrationClassifier(
        settings=NarrationClassifierSettings(
            base_url="http://localhost:11434/v1",
            model="qwen3:4b",
            provider="openai",
            batch_size=2,
        ),
        client=httpx.Client(transport=httpx.MockTransport(handle_request)),
    )
    completed_batch_sizes: list[int] = []

    classifier.classify(
        chunks=[
            NarrationChunk(id="chunk-1", text="I tighten the screw."),
            NarrationChunk(id="chunk-2", text="I pick up the drill."),
            NarrationChunk(id="chunk-3", text="I place the bracket here."),
        ],
        on_batch_complete=lambda batch: completed_batch_sizes.append(len(batch)),
    )

    assert completed_batch_sizes == [2, 1]


def test_openai_compatible_classifier__splits_invalid_batches() -> None:
    request_sizes: list[int] = []

    def handle_request(request: httpx.Request) -> httpx.Response:
        request_body = json.loads(request.content)
        user_content = request_body["messages"][1]["content"]
        chunks = json.loads(user_content.removesuffix("\n/no_think"))["chunks"]
        request_sizes.append(len(chunks))
        results = (
            []
            if len(chunks) > 1
            else [
                {
                    "id": chunks[0]["id"],
                    "label": "TASK",
                    "context_dependent": False,
                    "asr_unclear": False,
                    "reason": "Describes an action.",
                }
            ]
        )
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps({"results": results})}}]},
        )

    classifier = narration_classification.OpenAICompatibleNarrationClassifier(
        settings=NarrationClassifierSettings(
            base_url="http://localhost:11434/v1",
            model="qwen3:4b",
            provider="openai",
            batch_size=2,
            max_retries=0,
        ),
        client=httpx.Client(transport=httpx.MockTransport(handle_request)),
    )

    result = classifier.classify(
        chunks=[
            NarrationChunk(id="long-original-id-1", text="I tighten it."),
            NarrationChunk(id="long-original-id-2", text="I place it."),
        ]
    )

    assert request_sizes == [2, 1, 1]
    assert [item.chunk_id for item in result] == ["long-original-id-1", "long-original-id-2"]


def test_openai_compatible_classifier__rejects_missing_results() -> None:
    def handle_request(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"results": []}'}}]},
        )

    classifier = narration_classification.OpenAICompatibleNarrationClassifier(
        settings=NarrationClassifierSettings(
            base_url="http://localhost:11434/v1",
            model="qwen3:4b",
            provider="openai",
            max_retries=0,
        ),
        client=httpx.Client(transport=httpx.MockTransport(handle_request)),
    )

    with pytest.raises(ValueError, match="exactly one result"):
        classifier.classify(chunks=[NarrationChunk(id="chunk-1", text="This goes here.")])


@pytest.mark.parametrize(
    ("qualifying_words", "expected_status", "requirement_pass"),
    [
        (59, "likely_fail", False),
        (60, "manual_review", False),
        (70, "manual_review", True),
        (79, "manual_review", True),
        (80, "likely_pass", True),
    ],
)
def test_summarize_classifications__status_boundaries(
    qualifying_words: int,
    expected_status: str,
    requirement_pass: bool,
) -> None:
    chunks = [
        NarrationChunk(id="qualifying", text="word " * qualifying_words),
        NarrationChunk(id="other", text="word " * (100 - qualifying_words)),
    ]
    classifications = [
        NarrationClassification(
            chunk_id="qualifying",
            label="TASK",
            context_dependent=False,
            asr_unclear=False,
            reason="Task narration.",
        ),
        NarrationClassification(
            chunk_id="other",
            label="OTHER",
            context_dependent=False,
            asr_unclear=False,
            reason="Unrelated narration.",
        ),
    ]

    summary = narration_classification.summarize_classifications(
        chunks=chunks,
        classifications=classifications,
    )

    assert summary.qualifying_percentage == pytest.approx(float(qualifying_words))
    assert summary.status == expected_status
    assert summary.requirement_pass is requirement_pass


def test_summarize_classifications__counts_both_once_and_review_flags() -> None:
    chunks = [NarrationChunk(id="both", text="The red bracket is here and I tighten it")]
    classifications = [
        NarrationClassification(
            chunk_id="both",
            label="BOTH",
            context_dependent=True,
            asr_unclear=False,
            reason="Describes the scene and an action.",
        )
    ]

    summary = narration_classification.summarize_classifications(
        chunks=chunks,
        classifications=classifications,
    )

    assert summary.total_word_count == 9
    assert summary.qualifying_word_count == 9
    assert summary.label_word_counts == {"TASK": 0, "ENVIRONMENT": 0, "BOTH": 9, "OTHER": 0}
    assert summary.review_chunk_count == 1
