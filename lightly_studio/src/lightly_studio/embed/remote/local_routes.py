"""Adds the routes that prepare image bytes in this process to a remote embedder.

The import asks for capabilities that do not cross the wire, such as an image path or a
crop. A remote embedder that embeds image bytes gets a route for each of them.
"""

from __future__ import annotations

from lightly_studio_serve.embedder import (
    Embedder,
    ImageBytesEmbedder,
    ImageCropPathEmbedder,
    ImagePathEmbedder,
)

from lightly_studio.embed.remote import composition
from lightly_studio.embed.remote.embedder import RemoteEmbedder
from lightly_studio.embed.remote.image_crop_path_adapter import ImageCropPathRoute
from lightly_studio.embed.remote.image_path_adapter import ImagePathRoute

# Each capability interface with the route that serves it through the image-bytes route
_LOCAL_ROUTES: tuple[tuple[type[Embedder], type[RemoteEmbedder]], ...] = (
    (ImagePathEmbedder, ImagePathRoute),
    (ImageCropPathEmbedder, ImageCropPathRoute),
)


def with_local_routes(embedder: Embedder) -> Embedder:
    """Give a remote embedder with the image-bytes route the capabilities it prepares locally.

    Args:
        embedder: The embedder to adapt.

    Returns:
        A new embedder of the same server that also has each local route whose capability
        it does not implement, if ``embedder`` is a remote embedder that
        ``RemoteEmbedder.connect`` built and that embeds image bytes. Else ``embedder``.
    """
    if (
        not isinstance(embedder, RemoteEmbedder)
        or not composition.is_composed(cls=type(embedder))
        or not isinstance(embedder, ImageBytesEmbedder)
    ):
        return embedder
    adapted: RemoteEmbedder = embedder
    for interface, route in _LOCAL_ROUTES:
        if not isinstance(adapted, interface):
            adapted = adapted.with_route(route=route)
    return adapted
