"""Base classes a model is wrapped in to be served.

``BaseEmbedder`` carries the identity of the embedding space. One subclass per
input kind adds the method that embeds it, so a model implements only what it
supports and ``serve`` mounts exactly the matching endpoints.

These are the same classes LightlyStudio's own embedders derive from:
``lightly_studio.embed.embedder`` imports them from here and adds the capabilities
that only make sense in-process, such as reading an fsspec path.

A method that is mounted but unfinished raises
``lightly_studio_embed.CapabilityNotImplementedError``, which the server answers
501. Every other error is a failure of the model and answers 500.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from lightly_studio_embed.types import EmbeddingResult, EmbeddingSpaceSpec


class BaseEmbedder(ABC):
    """Identity of the embedding space a model produces.

    <span class="doc-badge doc-badge--beta">Beta</span>

    Subclass one or more of the capability classes below rather than this class
    directly: an embedder with no capability serves no embeddings.
    """

    __slots__ = ()

    @abstractmethod
    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        """Describe the embedding space this embedder produces.

        Returns:
            Metadata identifying the embedding space, stored so the same space
            can be recognized across LightlyStudio runs.
        """

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
    """Embeds text queries.

    <span class="doc-badge doc-badge--beta">Beta</span>
    """

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

    <span class="doc-badge doc-badge--beta">Beta</span>

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
    """Embeds videos passed as raw bytes.

    <span class="doc-badge doc-badge--beta">Beta</span>
    """

    __slots__ = ()

    @abstractmethod
    def embed_video_bytes(self, videos: list[bytes]) -> EmbeddingResult:
        """Embed a batch of videos given as encoded bytes.

        Args:
            videos: Encoded video bytes.

        Returns:
            The embeddings and the indices of the inputs they cover.
        """
