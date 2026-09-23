---
title: Embeddings API
description: Python API reference for LightlyStudio embeddings — register a custom embedder, implement the capability interfaces, and the supporting result types.
---

# Embeddings

!!! example "Beta API"
    The Embeddings API is in beta. Its interface may change in future
    releases without a deprecation period.

LightlyStudio embeds your data automatically on ingestion. To supply your own
embeddings — either computed on the fly or loaded from a precomputed store —
subclass the capability interfaces for the inputs you can embed and register the
embedder with [`register_default_embedder`](#register_default_embedder). The
registration must happen before you load a dataset or before the GUI is started.

See the [Embeddings page](../core_concepts/embeddings.md) for more details.

## register_default_embedder

::: lightly_studio.embed.public_api
    options:
        members: [register_default_embedder]

## Capability interfaces

An embedder subclasses `Embedder` through one interface per input it can embed.
Subclass only the capabilities your model provides.

### Embedder

::: lightly_studio_serve.embedder
    options:
        members: [Embedder]

### ImagePathEmbedder

::: lightly_studio_serve.embedder
    options:
        members: [ImagePathEmbedder]

### ImageCropPathEmbedder

::: lightly_studio_serve.embedder
    options:
        members: [ImageCropPathEmbedder]

### VideoPathEmbedder

::: lightly_studio_serve.embedder
    options:
        members: [VideoPathEmbedder]

### ImagePILEmbedder

::: lightly_studio_serve.embedder
    options:
        members: [ImagePILEmbedder]

### TextEmbedder

::: lightly_studio_serve.embedder
    options:
        members: [TextEmbedder]

### ImageBytesEmbedder

::: lightly_studio_serve.embedder
    options:
        members: [ImageBytesEmbedder]

<!-- TODO(Michal, 09/2026): Document VideoBytesEmbedder once LightlyStudio calls this
capability.

### VideoBytesEmbedder

::: lightly_studio_serve.embedder
    options:
        members: [VideoBytesEmbedder]
-->


## Supporting types

### EmbeddingSpaceSpec

::: lightly_studio_serve.types
    options:
        members: [EmbeddingSpaceSpec]

### EmbeddingResult

::: lightly_studio_serve.types
    options:
        members: [EmbeddingResult]

### ImageCrop

::: lightly_studio_serve.types
    options:
        members: [ImageCrop]
