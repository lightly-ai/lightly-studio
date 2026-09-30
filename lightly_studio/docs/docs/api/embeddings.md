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

## register_remote_embedder

::: lightly_studio.embed.public_api
    options:
        members: [register_remote_embedder]

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

## Serving

`lightly_studio_serve` serves an embedder over HTTP, so that
[`register_remote_embedder`](#register_remote_embedder) can connect a dataset to it. See
[Serving an embedder from a remote server](../core_concepts/embeddings.md#serving-an-embedder-from-a-remote-server).

### serve

::: lightly_studio_serve.server
    options:
        members: [serve]

### create_app

::: lightly_studio_serve.server
    options:
        members: [create_app]

### ServerLimits

::: lightly_studio_serve.protocol
    options:
        members: [ServerLimits]

### Protocol

Any server that speaks the protocol works, in any language. Version 1 has these endpoints.
`lightly_studio_serve.protocol` holds the paths and the request and response models.

| Endpoint | Body |
| --- | --- |
| `GET /v1/describe` | Response: `DescribeResponse`. The space key, dimension, capabilities and limits. |
| `POST /v1/embed/texts` | Request: `EmbedTextsRequest`. Response: `EmbeddingsResponse`. |
| `POST /v1/embed/images/bytes` | Request: multipart, one `files` part per image. Response: `EmbeddingsResponse`. |
| `POST /v1/embed/videos/bytes` | Request: multipart, one `files` part per video. Response: `EmbeddingsResponse`. |

A server mounts only the embed endpoints of the capabilities it reports. If the server has an
API key, each request must carry `Authorization: Bearer <api_key>`.

### Conformance check

```bash
lightly-studio-serve conformance <url> [--api-key KEY] [--probe-timeout SECONDS]
```

The command reads `/v1/describe`, then sends one probe to each capability that the server
reports.

| Argument | Description |
| --- | --- |
| `url` | The address of the server, for example `http://127.0.0.1:8080`. |
| `--api-key` | The bearer token. Default: the `LIGHTLY_STUDIO_SERVE_API_KEY` variable. |
| `--probe-timeout` | The seconds one probe can take. Default: 60. |

| Exit code | Meaning |
| --- | --- |
| `0` | The server passes. |
| `1` | The server fails, or the URL is not valid. |
| `2` | The arguments are not valid. |
