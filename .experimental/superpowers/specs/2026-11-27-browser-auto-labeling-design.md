# Browser auto-labeling (prototype)

Date: 2026-11-27. Status: prototype design, approved approach 1.

## Why

Auto-labeling today runs on the server: someone registers a `ls.LabelingModel` from the
Python client (`ls.register_labeling_model`), and the GUI calls it. Hosting inference is
costly and hard to deploy. Running the model on the user's GPU in the browser is free for
us and needs no setup from the user.

## Goals

- Anyone who opens LightlyStudio can auto-label object detection, with no Python model
  registered and no inference server.
- Stage 1: one image at a time in the image editor's existing **Auto-label** tool.
- Stage 2: many images at once from a grid selection.
- The model is LightlyTrain's LT-DETR (`ltdetrv2-s-coco`, 9.9M params, COCO, 640×640),
  exported to ONNX and run with onnxruntime-web.

## Non-goals

- Production hardening. This is a prototype: least code, no PR split, minimal tests.
- Instance segmentation in the browser. Object detection only.
- Other model families (RF-DETR, transformers.js). We own the LT-DETR license.
- Persisting suggestions or user-loaded model files across tab reloads.
- A dedicated review screen for batch results.

## Anti-goals

- Breaking or changing the existing server-side Auto-label path. Python-registered models
  keep working exactly as today, side by side with the browser model.
- Freezing the UI so badly during a batch that the user cannot browse.

## Constraints

- The ONNX export (`LTDETRObjectDetection.export_onnx` in lightly-train) has a fixed input
  `images` of shape `[B,3,640,640]`, and returns raw `logits` and normalized `cxcywh`
  `boxes`. Post-processing is not in the graph. Class names and normalization are stored
  in the ONNX metadata. Deformable attention is exported as gathers, with no GridSample
  and no custom ops.
- WebGPU is missing on Chrome and Firefox for Linux. The WASM fallback is slow but must
  work.
- Images are read from the backend's same-origin `/images/sample/{sample_id}`, so there is
  no CORS issue.

## Approaches considered

1. **Main thread, model from a configurable URL** (chosen). No backend change. Risk: UI
   jank in long batches. Picked because it's the least code, and stage 1 shows whether the
   jank happens.
2. Same, with inference in a hand-written Web Worker (onnxruntime's proxy worker does not
   support WebGPU). Smooth UI, about half a day more. Deferred until stage 1 shows jank.
3. The backend downloads and serves the model file. Works offline and self-hosted, but
   touches the backend. Rejected for the prototype.

## Design

### Model runtime (shared by both stages)

- One frontend module wraps onnxruntime-web: load the session (WebGPU execution provider,
  WASM fallback), preprocess, run, post-process. It returns predictions in the same
  `ModelAnnotationPreview` shape that the server endpoint returns, so the existing overlay
  and save code work unchanged.
- Preprocess and post-process mirror LightlyTrain's `preprocessor.preprocess_image` and
  `postprocessor.postprocess` for LT-DETR: resize, normalize from the metadata, sigmoid
  over the logits, top-k, threshold, convert `cxcywh` to pixel `xywh` of the original image.
- The default model, `ltdetrv2-s-coco`, is exported as fp16 ONNX and served from a URL in a
  frontend config value. It's downloaded on first use and cached with the browser Cache API.
- "Load model file (.onnx)…" accepts any LightlyTrain object detection ONNX export. Class
  names come from its metadata. The model lasts until the tab closes.
- The session loads once and is reused by both stages.

### Stage 1: single image (editor Auto-label tool)

- The Auto-label popup has one model list. Each model is tagged **Browser** or **Server**.
  The browser model is always listed, so the tool shows up even when no Python model is
  registered. The last item is "+ Load model file (.onnx)…".
- On the first run, the Run button shows the download progress ("Downloading 12 of 20 MB ·
  first run only"), then compiling.
- Everything after the run is today's flow: suggestions in the overlay, delete the wrong
  ones, Save N / Clear.

### Stage 2: batch from the grid

- With images selected in the grid, the selection pill gets an **✨ Auto-label** action. It
  asks for the model and confidence (the same controls as the popup), plus a class checklist
  of the model's classes, all ticked by default. Only ticked classes are saved, so a COCO
  run does not add 80 classes to the dataset unasked.
- A progress dock in the bottom right shows "87 of 240 · 312 annotations", a progress bar,
  and **Stop**. It stays visible while the user browses other pages of the dataset, and
  warns that closing the tab stops the run.
- Each image's annotations save as soon as that image finishes, into an annotation source
  named after the model (e.g. `ltdetrv2-s-coco`). Running again adds to that source. Stop
  keeps what's already saved.
- There is no review screen. When the run ends, the dock offers **View results**, which
  filters the grid by that annotation source. The user reviews and deletes wrong boxes with
  the existing grid and editor.

## Calls made after review (proposals, correct if wrong)

- **Demo branch, not merged.** The prototype stays on its branch and does not ship in the
  wheel. onnxruntime-web's WASM files load from the jsDelivr CDN, so the bundle stays small.
  No feature flag, license notice, or CI coverage work until a decision to ship.
- **Batch runs browser models only.** Server models stay in the single-image popup. The batch
  runner is a loop over the ONNX session; no per-image server requests and no
  segmentation masks.
- **License:** Lightly owns the LT-DETR weights. For an internal demo, no notice or accept
  step. Revisit hosting and notice if the feature ships.

## Left to the builder

- The config mechanism for the model URL, and where the fp16 ONNX is hosted for the demo.
- Where the dock lives in the layout so it survives route changes within a dataset.
- How the batch loop schedules images (one at a time is fine).
- Whether the existing preview save path is fast enough for hundreds of annotations, or
  needs a bulk create.
- Test depth: smoke tests for post-processing; the rest is manual.

## Results (2026-11-27, Apple Silicon Mac, Claude desktop browser pane, Chromium)

Model: `ltdetrv2-s-coco`, fp32 ONNX, 41.8 MB, input 640×640, 300 queries × 80 classes.

| Measurement | WebGPU | WASM (`?ep=wasm`) |
|---|---|---|
| Session creation | 3.5 s | 0.35 s |
| First image | 1.4 s (shader compile) | 1.1 s |
| Each later image, inference only | ~140 ms | ~1.1 s |
| Batch of 200 COCO val images, saves included | ~55 s (~0.27 s/image) | not measured |

- The first download is 42 MB from the dev server. Later loads come from Cache Storage in about 25 ms.
- The predictions look right on COCO val images (TV, chairs, person, stop sign, bear, teddy bears).
- **Batch UI:** the grid kept scrolling during a 200-image run with inference on the main thread, so the Web Worker (approach 2) isn't needed yet.
- **Stop:** a run stopped at 117 of 200 kept the 117 finished images.

**Not verified:**
- Stopping the run when leaving the collection by client-side navigation. The demo has one collection, and a synthetic `popstate` did not navigate.
- The `beforeunload` warning on tab close.
- A very large source image.
- A server model registered from Python, next to the browser model. Unit tests cover the server path.
- fp16 export.
