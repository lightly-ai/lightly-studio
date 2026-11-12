---
title: Labeling Models API
description: Python API reference for LightlyStudio labeling models — implement the LabelingModel interface and register a model that labels images in the GUI.
---

# Labeling Models

!!! example "Beta API"
    The Labeling Models API is in beta. Its interface may change in future
    releases without a deprecation period.

A labeling model suggests annotations for the open image in the GUI. Subclass
[`LabelingModel`](#labelingmodel) and register an instance with
[`register_labeling_model`](#register_labeling_model) before you start the GUI.

See the [Label with Your Own Model page](../workflows/labeling_models.md) for more details.

## register_labeling_model

::: lightly_studio.assisted_labeling.public_api
    options:
        members: [register_labeling_model]

## register_remote_labeling_model

::: lightly_studio.assisted_labeling.public_api
    options:
        members: [register_remote_labeling_model]

## LabelingModel

::: lightly_studio_serve.labeling_model
    options:
        members: [LabelingModel]

## ModelTask

::: lightly_studio_serve.labeling_model
    options:
        members: [ModelTask]

## PredictedAnnotation

::: lightly_studio_serve.types
    options:
        members: [PredictedAnnotation]

## Serving

Serve a labeling model with [`serve`](embeddings.md#serving) from `lightly_studio_serve`. Pass
the model as `labeling_model`. The server then has these endpoints:

| Endpoint | Purpose |
|---|---|
| `GET /v1/labeling/describe` | The model ID, the task, the annotation classes and the readiness. |
| `POST /v1/labeling/predict` | The predicted annotations of one image. |

The wire models are in `lightly_studio_serve.labeling_protocol`.
