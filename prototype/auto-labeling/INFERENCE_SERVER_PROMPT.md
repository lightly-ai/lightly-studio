# Implementation Prompt: SAM3 Annotation Server

Implement a small local HTTP inference server for the LightlyStudio auto-labeling prototype. Use **SAM3** for both batch and interactive inference. Keep model loading and serving in this server; do not modify LightlyStudio’s database or frontend.

## Runtime

- Python 3.10+, FastAPI, Uvicorn, and the official SAM3 implementation/checkpoint available in the environment.
- Read `SAM3_CHECKPOINT` and optional `SAM3_DEVICE` (`cuda`, `mps`, or `cpu`) from environment variables.
- Load the model once at startup. `GET /v1/describe` must report `ready: false` while loading and `ready: true` after successful loading.
- Bind to `127.0.0.1:8080` by default. Support an optional Bearer token from `SAM3_API_KEY`; require it when configured.

## Protocol

Base path is `/v1`. Return JSON errors with appropriate HTTP statuses: 400 malformed input, 401/403 auth failure, 413 body or batch too large, 422 decodable but unusable input, 429/503 temporary overload, 500 model failure, and 501 unsupported capability. Add `Retry-After` for 429/503.

### `GET /v1/describe`

Return:

```json
{
  "protocol_version": "1.0",
  "model_key": "sam3/local",
  "ready": true,
  "capabilities": [
    "segmentation_image_bytes",
    "object_detection_image_bytes"
  ],
  "supported_conditioning": ["targets", "points"],
  "limits": {"max_batch_size": 8, "max_request_bytes": 33554432}
}
```

`classes` is optional. Omit it for SAM3 open-vocabulary prompts. Capability names use singular `image`; route paths use plural `images`.

### `POST /v1/annotate/{task}/images/bytes`

Supported tasks are `segmentation` and `object_detection`. Accept `multipart/form-data` with repeated ordered file fields named `images` and a JSON form field named `conditioning`.

Target conditioning:

```json
{"targets":[{"prompt":"person on a bicycle","class_name":"cyclist"}]}
```

Point conditioning:

```json
{"points":[{"x":0.5,"y":0.25,"positive":true}]}
```

Points are normalized to `[0,1]`, apply to one image, and require at least one positive point. The client uses Shift-click for negative points. Targets apply to every image. Process each target as needed; never fail the whole batch because one image cannot be decoded.

Return:

```json
{
  "model_key":"sam3/local",
  "kept_indices":[0],
  "results":[[
    {
      "kind":"segmentation_mask",
      "class_name":"cyclist",
      "score":0.92,
      "image_width":640,
      "image_height":480,
      "encoding":"rle",
      "rle":[5,2,2,2,1]
    }
  ]]
}
```

`results[i]` corresponds to input `kept_indices[i]`. An empty prediction list means the image was processed successfully with no match. `kept_indices` must be unique, in bounds, and aligned with `results`.

Prediction rules:

- Every prediction has finite `score` in `[0,1]` and `class_name` (point inference may use an empty class name; Studio then uses the editor's selected class).
- `segmentation_mask` uses full-resolution, row-major integer RLE, alternating background/foreground runs and beginning with background, possibly zero. Run lengths must total `image_width * image_height`.
- `object_detection` uses normalized float XYWH in `bbox: [x,y,width,height]`.
- Include `image_width` and `image_height` for masks. `encoding` must be `"rle"`.
- Optional `track_id` may be ignored. Captions are not implemented.

For a segmentation request, return masks. For an object-detection request, return boxes; if SAM3 only produces masks, derive the tight normalized box from each mask.

## SAM3 adapter

Create a narrow adapter around the installed SAM3 API. Convert decoded PIL images to the model’s expected input, map target prompts and positive/negative points to SAM3 prompts, and normalize model outputs into the protocol above. Keep model-specific code out of the HTTP route handlers. Validate all output geometry and scores before responding.

## Completion criteria

The server starts with one documented command, loads SAM3 once, passes a health check through `/v1/describe`, accepts both target and point requests, returns protocol-valid masks/boxes with per-item skips, enforces the advertised batch/body limits, and includes a small README with a curl example for each request shape. Add focused unit tests for RLE conversion and protocol validation only if the host project already has a test harness.
