---
title: Embeddings API
description: Python API reference for LightlyStudio embeddings — register a custom embedding model, implement the generator protocols, and the supporting result types.
---

# Embeddings

LightlyStudio embeds your data automatically on ingestion. To supply your own
embeddings — either computed on the fly or loaded from a precomputed store —
implement one of the generator protocols below and register it with
[`set_default_embedding_model`](#set_default_embedding_model) before you create or
ingest a dataset.

See the [Embeddings concept page](../concepts_and_tools/embeddings.md) for an overview,
and the runnable examples for full implementations:

- `example_custom_embedding_model.py` — compute embeddings on the fly.
- `example_load_existing_embeddings.py` — load precomputed embeddings.

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
