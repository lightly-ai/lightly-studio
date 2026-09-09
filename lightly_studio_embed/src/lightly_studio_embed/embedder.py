"""Base classes a model is wrapped in to be served.

``BaseEmbedder`` carries the identity of the embedding space. One subclass per
input kind adds the method that embeds it, so a model implements only what it
supports and ``serve`` mounts exactly the matching endpoints.

The signatures mirror ``lightly_studio.embed.embedder``. The duplication is
deliberate: this package installs next to a customer's own torch pins, so it
cannot depend on ``lightly-studio``.

A method that is mounted but unfinished raises
``lightly_studio_embed.CapabilityNotImplementedError``, which the server answers
501. Every other error is a failure of the model and answers 500.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class EmbeddingResult:
    """Embeddings for the inputs that could be read, plus which inputs they cover.

    An embedder skips an input it cannot decode instead of failing the batch, so
    ``embeddings`` can have fewer rows than the input list.
    """

    embeddings: Sequence[Sequence[float]]
    """One row per entry of ``kept_indices``, each ``BaseEmbedder.dimension`` long.

    Pass a numpy array as ``array.tolist()``; the package stays free of numpy.
    """

    kept_indices: Sequence[int]
    """Indices into the input list of the inputs that were embedded, ascending."""


class BaseEmbedder(ABC):
    """Identity of the embedding space a model produces.

    Subclass one or more of the capability classes below rather than this class
    directly: an embedder with no capability serves no embeddings.
    """

    __slots__ = ()

    @property
    @abstractmethod
    def space_key(self) -> str:
        """Stable identifier of the embedding space.

        Two embedders sharing a ``space_key`` are treated as producing comparable
        vectors. Change it whenever they stop being comparable, e.g. for a model
        version change. Can be any string, e.g. ``your-company/model@v3``.
        """

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Length of every embedding vector this embedder returns."""

    @property
    def ready(self) -> bool:
        """Whether the model is loaded and can answer requests.

        The default suits a model loaded by the time the object exists. Override it
        when the model loads in the background: while it is ``False``,
        ``/v1/describe`` reports ``ready: false`` and the embed endpoints answer 503
        instead of running a half-loaded model.
        """
        return True


class TextEmbedder(BaseEmbedder):
    """Embeds text queries."""

    __slots__ = ()

    @abstractmethod
    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        """Embed a batch of text strings.

        Args:
            texts: The strings to embed.

        Returns:
            The embeddings and the indices of the inputs they cover.
        """


class ImageBytesEmbedder(BaseEmbedder):
    """Embeds images passed as raw bytes.

    Annotation crops arrive here too: LightlyStudio crops with a margin and posts
    the result, so an image-capable embedder supports them with no extra work.
    """

    __slots__ = ()

    @abstractmethod
    def embed_image_bytes(self, images: list[bytes]) -> EmbeddingResult:
        """Embed a batch of images given as encoded bytes.

        Sniff the format from the header rather than trusting the caller. JPEG, PNG
        and WebP are the formats the protocol allows.

        Args:
            images: Encoded image bytes.

        Returns:
            The embeddings and the indices of the inputs they cover.
        """


class VideoBytesEmbedder(BaseEmbedder):
    """Embeds videos passed as raw bytes."""

    __slots__ = ()

    @abstractmethod
    def embed_video_bytes(self, videos: list[bytes]) -> EmbeddingResult:
        """Embed a batch of videos given as encoded bytes.

        Args:
            videos: Encoded video bytes.

        Returns:
            The embeddings and the indices of the inputs they cover.
        """
