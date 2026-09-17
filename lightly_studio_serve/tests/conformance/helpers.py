"""What the conformance tests need to stand a server up in this process."""

from __future__ import annotations

import numpy as np
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lightly_studio_serve.conformance.client import ProbeResponse
from lightly_studio_serve.embedder import ImageBytesEmbedder, TextEmbedder, VideoBytesEmbedder
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec

SPACE_KEY = "acme/model@v1"
DIMENSION = 2


class AppProbeClient:
    """Sends the probes to an application in this process, so a run opens no port."""

    def __init__(self, app: FastAPI, api_key: str | None = None) -> None:
        headers = {} if api_key is None else {"Authorization": f"Bearer {api_key}"}
        self.client = TestClient(app, headers=headers)

    # The client sends to this process, so there is nothing for a timeout to cut short.
    def get(self, path: str, timeout: float) -> ProbeResponse:
        response = self.client.get(path)
        return ProbeResponse(status_code=response.status_code, body=response.content)

    def post(self, path: str, content_type: str, body: bytes, timeout: float) -> ProbeResponse:
        response = self.client.post(path, content=body, headers={"Content-Type": content_type})
        return ProbeResponse(status_code=response.status_code, body=response.content)


class FakeEmbedder(TextEmbedder, ImageBytesEmbedder, VideoBytesEmbedder):
    """Serves every capability that version 1 mounts, with one fixed row per item."""

    def __init__(self, ready: bool = True) -> None:
        self.is_ready = ready

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key=SPACE_KEY, dimension=DIMENSION)

    @property
    def ready(self) -> bool:
        return self.is_ready

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        return _rows(count=len(texts))

    def embed_image_bytes(self, images: list[bytes]) -> EmbeddingResult:
        return _rows(count=len(images))

    def embed_video_bytes(self, videos: list[bytes]) -> EmbeddingResult:
        return _rows(count=len(videos))


def _rows(count: int) -> EmbeddingResult:
    embeddings = np.array([[0.5, -0.5]] * count, dtype=np.float32).reshape(count, DIMENSION)
    return EmbeddingResult(embeddings=embeddings, kept_indices=list(range(count)))
