"""Reference implementation of the LightlyStudio embedding service contract.

Run this on your own network to keep text and image search working for a dataset that
was indexed with your own embedding model. The browser calls this service directly, so
it never sends your model or your queries to Lightly.

The model below is MobileCLIP, to keep the example runnable. Replace the three
`_embed_*` bodies with your own model and set MODEL_ID to a string you bump whenever the
output vectors change.

Run it with:

    uv run uvicorn lightly_studio.examples.example_embedding_service:app --port 8123

Then register the URL when you index, or set it later in the GUI:

    ls.set_default_embedding_model(
        MyGenerator(), serving_url="http://localhost:8123"
    )

The endpoints are:

    GET  /info         -> capabilities and model identity
    POST /embed/text   -> {"text": "..."}         -> [0.1, ...]
    POST /embed/image  -> multipart file "image"  -> [0.1, ...]
"""

from __future__ import annotations

import io
from collections.abc import Awaitable, Callable
from typing import Annotated

import torch
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from lightly_studio.dataset import file_utils
from lightly_studio.dataset.env import LIGHTLY_STUDIO_MODEL_CACHE_DIR
from lightly_studio.vendor import mobileclip

# Bump this whenever the model produces different vectors. It must match the
# embedding_model_hash your indexing generator declares, otherwise LightlyStudio disables
# search rather than compare vectors from two different embedding spaces.
MODEL_ID = "mobileclip_s0"

# Origins allowed to call this service. Set this to the LightlyStudio URL your users open.
# CORS is not authentication: it stops other websites from reading responses in a browser,
# it does not stop anything on this network from calling the service directly.
ALLOWED_ORIGINS = ["*"]

CONTRACT_VERSION = "1"
EMBEDDING_DIMENSION = 512
_MOBILECLIP_MODEL_NAME = "mobileclip_s0"
_MOBILECLIP_DOWNLOAD_URL = (
    f"https://docs-assets.developer.apple.com/ml-research/datasets/mobileclip/"
    f"{_MOBILECLIP_MODEL_NAME}.pt"
)


class ServiceInfo(BaseModel):
    """What this service can do, fetched once before the search bar renders.

    Attributes:
        contract_version: Version of the wire contract this service speaks.
        model_id: Must equal the embedding_model_hash the stored vectors were indexed with.
        embedding_dimension: Length of the returned vectors.
        supports_text: False for a model with no text tower, which hides the text search box.
        supports_image: False for a model that cannot embed images.
        normalized: Whether returned vectors are unit length.
    """

    contract_version: str
    model_id: str
    embedding_dimension: int
    supports_text: bool
    supports_image: bool
    normalized: bool


class EmbedTextRequest(BaseModel):
    """Request body for text embedding."""

    text: str


class PrivateNetworkAccessMiddleware(BaseHTTPMiddleware):
    """Answer Chrome's private-network preflight.

    An HTTPS page on a public origin calling a host on a private network triggers a
    preflight that Chrome only accepts if the response carries this header. Without it the
    browser blocks the request before this service ever sees the real call.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Add the private-network header to preflight responses."""
        response = await call_next(request)
        if request.headers.get("Access-Control-Request-Private-Network") == "true":
            response.headers["Access-Control-Allow-Private-Network"] = "true"
        return response


app = FastAPI(title="LightlyStudio embedding service")

# CORSMiddleware is added first so that it ends up inside the private-network middleware,
# which needs to add its header to the preflight response CORSMiddleware produces.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=3600,
)
app.add_middleware(PrivateNetworkAccessMiddleware)


@app.get("/info")
def read_info() -> ServiceInfo:
    """Report the model identity and capabilities."""
    return ServiceInfo(
        contract_version=CONTRACT_VERSION,
        model_id=MODEL_ID,
        embedding_dimension=EMBEDDING_DIMENSION,
        supports_text=True,
        supports_image=True,
        # MobileCLIP does not normalize its outputs. PerceptionEncoder does.
        normalized=False,
    )


@app.post("/embed/text")
def embed_text(request: EmbedTextRequest) -> list[float]:
    """Embed a search query into the same space as the indexed images."""
    model = _get_model()
    tokenized = model.tokenizer([request.text]).to(model.device)
    with torch.no_grad():
        embedding = model.model.encode_text(tokenized)[0]  # type: ignore[operator]
    embedding_list: list[float] = embedding.cpu().numpy().flatten().tolist()
    return embedding_list


@app.post("/embed/image")
def embed_image(
    image: Annotated[UploadFile, File(description="The image to embed.")],
) -> list[float]:
    """Embed a query image. This service owns all preprocessing."""
    model = _get_model()
    pil_image = Image.open(io.BytesIO(image.file.read())).convert("RGB")
    image_tensor = model.preprocess(pil_image).unsqueeze(0).to(model.device)
    with torch.no_grad():
        embedding = model.model.encode_image(image_tensor)[0]  # type: ignore[operator]
    embedding_list: list[float] = embedding.cpu().numpy().flatten().tolist()
    return embedding_list


class _MobileCLIP:
    """MobileCLIP weights, tokenizer and preprocessing, loaded once."""

    def __init__(self) -> None:
        """Download the checkpoint if needed and move the model onto the best device."""
        checkpoint_path = LIGHTLY_STUDIO_MODEL_CACHE_DIR / f"{_MOBILECLIP_MODEL_NAME}.pt"
        file_utils.download_file_if_does_not_exist(
            url=_MOBILECLIP_DOWNLOAD_URL, local_filename=checkpoint_path
        )
        self.model, _, self.preprocess = mobileclip.create_model_and_transforms(
            model_name=_MOBILECLIP_MODEL_NAME, pretrained=str(checkpoint_path)
        )
        self.device = torch.device(
            "cuda"
            if torch.cuda.is_available()
            else "mps"
            if torch.backends.mps.is_available()
            else "cpu"
        )
        self.model = self.model.to(self.device)
        self.tokenizer = mobileclip.get_tokenizer(model_name=_MOBILECLIP_MODEL_NAME)


_model: _MobileCLIP | None = None


def _get_model() -> _MobileCLIP:
    """Load the model on first use so startup does not block on the download."""
    global _model  # noqa: PLW0603 one model per process, one port per model.
    if _model is None:
        _model = _MobileCLIP()
    return _model
