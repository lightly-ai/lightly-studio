# Auto-labeling prototype protocol

Prototype-only additions to the supplied synchronous embedding contract. The UX specification at `/Users/jonaswurst/Lightly/lightly-studio/AUTO_LABELING_UX_PROTOTYPE.md` owns scope. No model server is implemented here.

## Model server

Configure `LIGHTLY_STUDIO_ANNOTATION_URL` (base URL, default `http://localhost:8080`) and optional `LIGHTLY_STUDIO_ANNOTATION_API_KEY`. No redirects. Bearer key required outside loopback. Local/LAN endpoints are supported for this local prototype.

`GET /v1/describe` (5 second timeout) returns:

```json
{"protocol_version":"1.0","model_key":"sam3/local","ready":true,"capabilities":["segmentation_image_bytes","object_detection_image_bytes"],"supported_conditioning":["targets","points"],"limits":{"max_batch_size":8,"max_request_bytes":33554432}}
```

Optional `classes: string[]` means closed-set; absent means open vocabulary. Embed-only identity fields are not required. Capability names use singular `image`; routes use plural `images`, matching the embedding contract. Task names: `segmentation`, `object_detection`, `classification` (reserved for compatible prediction parsing; batch UI offers only first two).

`POST /v1/annotate/{task}/images/bytes`: multipart with repeated ordered file parts named `images` and a JSON form string named `conditioning`. Send original image bytes, never paths. `conditioning` is either `{"targets":[{"prompt":"person on a bicycle","class_name":"cyclist"}]}` or `{"points":[{"x":0.5,"y":0.25,"positive":true}]}`. Points use normalized coordinates in [0,1], share one image (N=1), and require at least one positive point. Shift-click places a negative point. Targets apply to every image. The model returns raw scores; Studio applies the floor.

```json
{"model_key":"sam3/local","kept_indices":[0],"results":[[{"kind":"segmentation_mask","class_name":"cyclist","score":0.92,"image_width":4,"image_height":3,"encoding":"rle","rle":[5,2,2,2,1]}]]}
```

`results[i]` corresponds to input `kept_indices[i]`. Empty predictions means successful processing with no matches; omitted input means skipped. Indices must be unique and in bounds; counts must match. Model identity must match discovery.

Prediction kinds: `object_detection` with `bbox: [x,y,width,height]` normalized XYWH; `segmentation_mask` with full-resolution row-major `rle` alternating background/foreground run lengths, always beginning with background (possibly zero); `classification` without geometry. All require finite `score` in [0,1] and `class_name` (point output may use empty string because the editor chooses the class). Masks require positive `image_width`, `image_height`, `encoding: "rle"`, nonnegative integer runs totaling width*height. Dimension mismatch is an error. Optional `track_id` is ignored. Caption is reserved and not persisted in this prototype.

Detection runs may derive boxes from returned masks; segmentation runs only persist masks. Interactive requests always ask for segmentation so output can switch Mask/Box without another model call. Multiple interactive masks: preview the highest-scoring nonempty mask. Studio converts full-image masks to its bbox-cropped mask representation at the boundary.

Reuse supplied HTTP errors: 400/401/403/422/500 fail; 413 split batches (single item fails); 429/503 bounded retries respecting Retry-After; 501 refresh discovery and fail. Respect advertised batch/body limits. Synchronous inference timeout 120 seconds per call.

## Studio API

All routes under `/api/annotate` (existing app prefix conventions apply).

- `GET /describe`: descriptor above plus `endpoint`; unavailable model produces an actionable API error, never secrets.
- `POST /batch`: `{collection_id, filter, task, targets, confidence_threshold}`; `filter` is existing GridFilter, task `object_detection` or `segmentation`. Snapshot filtered image IDs once. Return `{source_id, source_name, annotations_created, images_processed, images_skipped, unmatched_prompts}`. Always create a unique source, even for zero matches; record processed coverage including empty predictions.
- `POST /interactive`: `{collection_id, sample_id, points}`. Read original image in backend. Return `{prediction, latency_ms}`; prediction is null or `{bbox: {x,y,width,height}, segmentation_mask: number[], score, class_name}` using an absolute integer bbox and RLE cropped to that bbox. Studio expands the mask to full-image coordinates before commit. `class_name` is used to create/select the annotation class automatically; an empty value falls back to the editor's selected class, then to the generic `object` class. Never persist here; the editor commits through the normal annotation resolver path after preview confirmation.

Source deletion uses the existing `DELETE /collections/{collection_id}` route with corrected annotation cascade and coverage cleanup. Existing collection read supplies annotation count for confirmation.
