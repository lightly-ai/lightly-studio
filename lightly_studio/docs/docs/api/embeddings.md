---
title: Embeddings API
description: Python API reference for LightlyStudio embeddings — register a custom embedding model, implement the generator protocols, and the supporting result types.
---

# Embeddings

!!! example "Beta API"
    The Embeddings API is in beta. Its interface may change in future
    releases without a deprecation period.

LightlyStudio embeds your data automatically on ingestion. To supply your own
embeddings — either computed on the fly or loaded from a precomputed store —
implement one of the generator protocols below and register it with
[`set_default_embedding_model`](#set_default_embedding_model). The registration
must happen before you load a dataset or before the GUI is started.

See the [Embeddings page](../core_concepts/embeddings.md) for more details.

<!-- TODO(Michal, 09/2026): Restore the API reference below. The autodoc blocks
     for set_default_embedding_model and the EmbeddingGenerator protocols were
     removed with EmbeddingManager; document their registry-based replacements
     in a follow-up. -->

## set_default_embedding_model

## Generator protocols

### EmbeddingGenerator

### ImageEmbeddingGenerator

### VideoEmbeddingGenerator

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
