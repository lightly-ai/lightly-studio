---
title: Embeddings API
description: Python API reference for LightlyStudio embeddings — register a custom embedding model, implement the generator protocols, and the supporting result types.
---

# Embeddings

!!! experimental "Beta API"
    The Embeddings API is in beta. Its interface may change in future
    releases without a deprecation period.

LightlyStudio embeds your data automatically on ingestion. To supply your own
embeddings — either computed on the fly or loaded from a precomputed store —
implement one of the generator protocols below and register it with
[`set_default_embedding_model`](#set_default_embedding_model) before you create or
ingest a dataset.

See the [Embeddings page](../concepts_and_tools/embeddings.md) for more details.

## set_default_embedding_model

::: lightly_studio.dataset.embedding_manager
    options:
        members: [set_default_embedding_model]

## Generator protocols

### EmbeddingGenerator

::: lightly_studio.dataset.embedding_generator
    options:
        members: [EmbeddingGenerator]

### ImageEmbeddingGenerator

::: lightly_studio.dataset.embedding_generator
    options:
        members: [ImageEmbeddingGenerator]

### VideoEmbeddingGenerator

::: lightly_studio.dataset.embedding_generator
    options:
        members: [VideoEmbeddingGenerator]

## Supporting types

### EmbeddingResult

::: lightly_studio.dataset.embedding_result
    options:
        members: [EmbeddingResult]

### ImageCrop

::: lightly_studio.dataset.embedding_generator
    options:
        members: [ImageCrop]
