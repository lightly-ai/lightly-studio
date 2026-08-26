"""Example of how to register a custom embedder with the new embedder API.

This is the new-API counterpart of ``example_custom_embedding_model.py``. It
shows how a user brings their own model by implementing the embedder protocols
from ``lightly_studio.embed`` and registering it with ``register_default_embedder``.

A single embedder here handles both images (at ingest) and text (for GUI search).
Because it implements ``embed_images`` and ``embed_text``, the registry routes it
into the image-path *and* the text slot, so the query text is embedded by the same
model that produced the stored image vectors. Cosine similarity only makes sense
in a shared space, so one embedder for both sides is what makes text search work.

The vectors here are random, so search results are not semantically meaningful.
That is on purpose: this prototype is about the wiring, not the model quality.
Swap the body of ``_vector`` for a real model and everything downstream is the same.

Register the embedder with ``register_default_embedder`` BEFORE creating a dataset,
so ingestion uses your embedder instead of the built-in ``RandomEmbedder``.
"""

from __future__ import annotations

import hashlib

import numpy as np
from environs import Env
from numpy.typing import NDArray

import lightly_studio as ls
from lightly_studio.database import db_manager
from lightly_studio.dataset.embedding_result import EmbeddingResult
from lightly_studio.embed.base_embedder import BaseEmbedder
from lightly_studio.embed.capability import EmbedderDescriptor
from lightly_studio.embed.manager import register_default_embedder

MODEL_ID = "example-random-embedder"
EMBEDDING_DIMENSION = 64


class CustomEmbedder(BaseEmbedder):
    """A custom image-and-text embedder.

    It inherits ``BaseEmbedder`` for the identity and capability plumbing and adds
    ``embed_images`` and ``embed_text``. The registry derives the capabilities from
    the methods present, so no manual capability declaration is needed. Implementing
    only one of the two methods would make this an image-only or text-only embedder.

    The vectors are deterministic per input (seeded from a hash of the path or text),
    so re-running the example gives stable results, but they are still random noise.
    """

    def load(self) -> EmbedderDescriptor:
        """Realize the model and report its identity and capabilities.

        A real embedder loads its weights here, once, before any embed call, so
        constructing the embedder stays cheap.
        """
        return self._descriptor(model_id=MODEL_ID, dimension=EMBEDDING_DIMENSION)

    def embed_images(self, paths: list[str]) -> EmbeddingResult:
        """Embed images referenced by path. Called by the ingest path."""
        return self._embed(keys=paths)

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        """Embed query text. Called by the GUI text-search route."""
        return self._embed(keys=texts)

    def _embed(self, keys: list[str]) -> EmbeddingResult:
        """Turn each input key into a deterministic random vector."""
        embeddings = np.stack([self._vector(key) for key in keys], axis=0).astype(np.float32)
        return EmbeddingResult(embeddings=embeddings, kept_indices=list(range(len(keys))))

    def _vector(self, key: str) -> NDArray[np.float64]:
        """Return a stable random vector of shape ``(EMBEDDING_DIMENSION,)`` for ``key``.

        ``key`` is an image path or a text string.
        """
        digest = hashlib.sha256(key.encode("utf-8")).digest()
        seed = int.from_bytes(digest[:8], byteorder="big")
        return np.random.default_rng(seed).random(EMBEDDING_DIMENSION)


# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Register the custom embedder BEFORE creating the dataset. This overrides the
# built-in RandomEmbedder for every collection and for both image and text.
register_default_embedder(CustomEmbedder())

# Define the path to the dataset directory
dataset_path = env.path("EXAMPLES_DATASET_PATH")

# Create a Dataset from a path. Images are embedded with the custom embedder.
dataset = ls.ImageDataset.create()
dataset.add_images_from_path(path=str(dataset_path))

# Text search in the GUI now embeds the query with CustomEmbedder, matching the
# vectors stored at ingest.
ls.start_gui()
