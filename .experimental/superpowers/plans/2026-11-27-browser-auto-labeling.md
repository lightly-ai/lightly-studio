# Browser Auto-Labeling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run LightlyTrain's LT-DETR in the browser with onnxruntime-web, for one image in the
editor's Auto-label tool and for a grid selection.

**Architecture:** A small `browserInference` module turns an ONNX file into a `Detector`
(onnxruntime-web, WebGPU with WASM fallback, main thread). A global `useBrowserModels` store
lists browser models next to the server's models. Stage 1 branches the existing
`useLabelWithModel.generate`. Stage 2 adds a selection-pill action, a dialog, a batch runner and
a progress dock that saves into an annotation source named after the model.

**Tech Stack:** SvelteKit, Svelte 5, TypeScript, TanStack Query, onnxruntime-web, vitest.

**Spec:** `.experimental/superpowers/specs/2026-11-27-browser-auto-labeling-design.md`

## Global Constraints

- Prototype on a demo branch: no PR split, tests only for pure logic and the stage 1 branch.
- The server Auto-label path keeps working unchanged next to the browser model.
- `onnxruntime-web` is imported dynamically (`import('onnxruntime-web/webgpu')`), so no eagerly
  loaded chunk grows past 500 KB. WASM files load from
  `https://cdn.jsdelivr.net/npm/onnxruntime-web@<installed version>/dist/`.
- Default model: `ltdetrv2-s-coco`, exported as **fp32** with batch size 1 (call made while
  planning: fp32 avoids fp16 numeric issues on WebGPU; switch to fp16 once it works). Served at
  `/models/ltdetrv2-s-coco.onnx` from `lightly_studio_view/static/models/` (gitignored).
- ONNX contract: input `images` `[1,3,H,W]` float32; outputs `logits` `[1,Q,C]` and `boxes`
  `[1,Q,4]` normalized `cxcywh`. Metadata keys `classes` (JSON object id→name, insertion order
  = internal class index) and `image_normalize` (JSON `{mean, std}`).
- Pre/post-processing mirrors `lightly_train/_pre_post_processing/object_detection.py`: stretch
  resize to H×W (no letterbox), scale to [0,1], normalize; sigmoid, flattened top-k (k = 300),
  `label = index % C`, `query = index // C`, keep `score > threshold` (strict).
- Batch runs browser models only, saves with `saveAs: 'box'` and
  `annotationSource: <model id>`.
- Run frontend commands from `lightly_studio_view` after `nvm use`.

## Review Focus

1. A `classes` JSON whose ids are not ascending (`{"5":"b","1":"a"}`) must keep insertion
   order; `JSON.parse` reorders integer keys. Test in Task 2.
2. RGBA images with transparent pixels must ignore alpha, not darken. Test in Task 2.
3. Huge source images (8000 px) must not allocate a full-size canvas: decode with
   `createImageBitmap(blob, { resizeWidth, resizeHeight })`. Manual check in Task 8.
4. No WebGPU (Linux Chrome, Firefox on Intel Macs) must fall back to WASM, not error. Manual
   check in Task 8 with `?ep=wasm`.
5. Leaving the collection or closing the tab mid-batch: the tab close warns, and leaving the
   collection stops the run with the saved images kept. Manual check in Task 8.

---

### Task 1: Setup and model export

**Files:**
- Create: `.experimental/browser-auto-labeling/export_model.py`
- Modify: `.gitignore` (add `lightly_studio_view/static/models/`)
- Modify: `lightly_studio_view/package.json` (add `onnxruntime-web`)

- [ ] **Step 1: Generate the worktree's missing files**

Run, from the worktree root: `cd lightly_studio && make export-schema && make export-version && cd ../lightly_studio_view && nvm use && npm ci && npm run generate-api-client && npm run generate-language`
Expected: `src/lib/api/lightly_studio_local/types.gen.ts` exists.

- [ ] **Step 2: Write `export_model.py`**

Loads `lightly_train.load_model("ltdetrv2-s-coco")` and calls
`export_onnx(out, precision="fp32", dynamic_batch_size=False)` with
`out = lightly_studio_view/static/models/ltdetrv2-s-coco.onnx`. Print the file size.

- [ ] **Step 3: Run it**

Run: `uv run --with lightly-train python .experimental/browser-auto-labeling/export_model.py`
Expected: the `.onnx` file exists, about 40 MB.

- [ ] **Step 4: Install onnxruntime-web**

Run: `npm install onnxruntime-web` in `lightly_studio_view`.
Expected: `package.json` lists it, and `git status` does not show the `.onnx` file.

- [ ] **Step 5: Commit** `.gitignore`, `package.json`, `package-lock.json`, `export_model.py`.

### Task 2: Pure ONNX helpers

**Files:**
- Create: `lightly_studio_view/src/lib/browserInference/onnxMetadata.ts`
- Create: `lightly_studio_view/src/lib/browserInference/detection.ts`
- Create: `lightly_studio_view/src/lib/browserInference/index.ts` (barrel)
- Create: `lightly_studio_view/src/lib/browserInference/testHelpers.ts` (`encodeModel`)
- Test: `onnxMetadata.test.ts`, `detection.test.ts` next to them

**Interfaces:**
- Produces:
  - `readOnnxMetadata(bytes: Uint8Array): Record<string, string>`
  - `parseClassNames(classesJson: string): string[]` (values in insertion order)
  - `toInputTensor(params: { rgba: Uint8ClampedArray; width: number; height: number; normalize: { mean: number[]; std: number[] } | null }): Float32Array` (CHW)
  - `decodeDetections(params: { logits: Float32Array; boxes: Float32Array; numClasses: number; classNames: string[]; imageWidth: number; imageHeight: number; threshold: number; topK: number }): ModelAnnotationPreview[]`

- [ ] **Step 1: Write the failing tests**

```ts
// onnxMetadata.test.ts. encodeModel lives in src/lib/browserInference/testHelpers.ts (Task 4
// reuses it). It builds a ModelProto by hand: field 1 varint
// (0x08, 8), field 7 bytes (0x3a, len, junk) to prove skipping, then one field 14
// (0x72) per entry holding key (0x0a) and value (0x12) strings.
it('reads metadata_props and skips other fields', () => {
    const bytes = encodeModel({ classes: '{"0":"person"}', model_name: 'ltdetrv2-s-coco' });
    expect(readOnnxMetadata(bytes)).toEqual({ classes: '{"0":"person"}', model_name: 'ltdetrv2-s-coco' });
});
it('keeps insertion order of class ids', () => {
    expect(parseClassNames('{"5":"b","1":"a"}')).toEqual(['b', 'a']);
});

// detection.test.ts
it('converts RGBA to normalized CHW and ignores alpha', () => {
    const rgba = new Uint8ClampedArray([255, 0, 0, 255, 0, 255, 0, 0]);
    const out = toInputTensor({ rgba, width: 2, height: 1, normalize: { mean: [0.5, 0.5, 0.5], std: [0.5, 0.5, 0.5] } });
    expect(Array.from(out)).toEqual([1, -1, -1, 1, -1, -1]);
});
const params = {
    logits: new Float32Array([2, -5, -5, 0]), // q0: person, q1: car
    boxes: new Float32Array([0.5, 0.5, 0.5, 0.5, 0.25, 0.25, 0.1, 0.1]),
    numClasses: 2, classNames: ['person', 'car'], imageWidth: 200, imageHeight: 100, topK: 300
};
it('keeps scores strictly above the threshold, in pixel xywh', () => {
    const [only, ...rest] = decodeDetections({ ...params, threshold: 0.6 });
    expect(rest).toEqual([]);
    expect(only).toMatchObject({ class_name: 'person', bbox: { x: 50, y: 25, width: 100, height: 50 }, segmentation_mask: null });
    expect(only.score).toBeCloseTo(0.8808, 4);
    expect(decodeDetections({ ...params, threshold: 0.5 })).toHaveLength(1); // sigmoid(0) = 0.5 is not > 0.5
});
it('returns lower-scored objects for a lower threshold', () => {
    const result = decodeDetections({ ...params, threshold: 0.4 });
    expect(result[1]).toMatchObject({ class_name: 'car', bbox: { x: 40, y: 20, width: 20, height: 10 } });
});
```

- [ ] **Step 2: Run them to verify they fail**

Run: `npx vitest run src/lib/browserInference`
Expected: FAIL, modules not found.

- [ ] **Step 3: Implement the four functions**

`readOnnxMetadata`: walk top-level protobuf fields. Read the varint tag; wire type 0 → skip the
varint, 1 → skip 8 bytes, 2 → read the varint length (decode it as a Number, not with 32-bit bit
ops, since the graph field can exceed 2^31), 5 → skip 4 bytes. For field 14, decode the
sub-message's fields 1 and 2 as UTF-8. `parseClassNames`: match
`/"((?:[^"\\]|\\.)*)"\s*:\s*("(?:[^"\\]|\\.)*")/g` and `JSON.parse` each value.
`decodeDetections`: sigmoid all, take the top `min(topK, Q*C)` by score, decode as in Global
Constraints, round each xyxy corner and derive width/height from the rounded corners.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npx vitest run src/lib/browserInference`
Expected: PASS.

- [ ] **Step 5: Commit**

### Task 3: Detector and model loading

**Files:**
- Create: `lightly_studio_view/src/lib/browserInference/createDetector.ts`
- Create: `lightly_studio_view/src/lib/browserInference/fetchModelBytes.ts`
- Create: `lightly_studio_view/src/lib/browserInference/loadImageBitmap.ts`

**Interfaces:**
- Consumes: Task 2 functions.
- Produces:
  - `createDetector(bytes: Uint8Array, options?: { executionProvider?: 'webgpu' | 'wasm' }): Promise<Detector>`
    where `Detector = { classNames: string[]; inputSize: { width: number; height: number }; executionProvider: 'webgpu' | 'wasm'; detect(image: ImageBitmap, original: { width: number; height: number }, threshold: number): Promise<ModelAnnotationPreview[]> }`
  - `fetchModelBytes(url: string, onProgress: (loaded: number, total: number) => void): Promise<Uint8Array>`
  - `loadImageBitmap(sampleId: string, size: { width: number; height: number }): Promise<{ bitmap: ImageBitmap; original: { width: number; height: number } }>`

- [ ] **Step 1: Implement `fetchModelBytes`**

Cache name `lightly-browser-models`. On a cache hit, return the bytes. Otherwise, stream the
response, call `onProgress` per chunk (total from `content-length`), put a copy in the cache.

- [ ] **Step 2: Implement `loadImageBitmap`**

`fetch(getImageURLById(sampleId))` → blob. Read the original size with a plain
`createImageBitmap(blob)` (then `close()` it), and the model input with
`createImageBitmap(blob, { resizeWidth, resizeHeight, resizeQuality: 'high' })`.

- [ ] **Step 3: Implement `createDetector`**

Dynamic import of `onnxruntime-web/webgpu`; set `env.wasm.wasmPaths` to the jsDelivr URL.
Provider: `options.executionProvider` if given (read `?ep=` from `location.search` in the caller),
else `webgpu` when `navigator.gpu` exists, falling back to `wasm` if session creation throws.
Input H×W: `session.inputMetadata` dims if present, else 640×640. `detect` draws the bitmap on an
`OffscreenCanvas`, then runs `toInputTensor` → `session.run({ images })` → `decodeDetections`
with `topK: 300`.

- [ ] **Step 4: Verify in the browser**

Run `npm run dev`, open any page, and in the console import the module through Vite
(`await import('/src/lib/browserInference/index.ts')`). Fetch the model, create a detector, and
detect on one sample ID.
Expected: COCO class names and plausible boxes; log the provider and ms per image.

- [ ] **Step 5: Commit**

### Task 4: `useBrowserModels` store

**Files:**
- Create: `lightly_studio_view/src/lib/hooks/useBrowserModels/useBrowserModels.ts`
- Test: `lightly_studio_view/src/lib/hooks/useBrowserModels/useBrowserModels.test.ts`
- Modify: `lightly_studio_view/src/lib/hooks/index.ts` (export)

**Interfaces:**
- Consumes: `createDetector`, `fetchModelBytes`, `readOnnxMetadata`, `parseClassNames`.
- Produces: `useBrowserModels(): { models: Readable<BrowserModel[]>; loadProgress: Readable<{ modelId: string; loaded: number; total: number } | null>; getDetector(modelId: string): Promise<Detector>; addModelFile(file: File): Promise<string> }`.
  `BrowserModel = { id: string; task: 'object_detection'; class_names: string[]; runsIn: 'browser' }`.
  State is module-level, so every caller shares it. The default entry is `ltdetrv2-s-coco`
  with `class_names: []` until its detector loads.

- [ ] **Step 1: Write the failing tests** (mock `$lib/browserInference` `createDetector` and `fetchModelBytes`)

```ts
it('lists the default model before anything loads', () => {
    expect(get(useBrowserModels().models).map((m) => m.id)).toEqual(['ltdetrv2-s-coco']);
});
it('creates one detector per model and fills its classes', async () => {
    const { getDetector, models } = useBrowserModels();
    await Promise.all([getDetector('ltdetrv2-s-coco'), getDetector('ltdetrv2-s-coco')]);
    expect(createDetector).toHaveBeenCalledTimes(1);
    expect(get(models)[0].class_names).toEqual(['person', 'car']);
});
it('adds a model file with classes from its metadata', async () => {
    const id = await useBrowserModels().addModelFile(new File([encodeModel({ classes: '{"0":"forklift"}' })], 'forklifts.onnx'));
    expect(id).toBe('forklifts');
    expect(get(useBrowserModels().models).find((m) => m.id === id)?.class_names).toEqual(['forklift']);
});
```

- [ ] **Step 2: Run them to verify they fail**, `npx vitest run src/lib/hooks/useBrowserModels`
- [ ] **Step 3: Implement.** A file model keeps its `File` in a module-level map, and `getDetector` reads it with `file.arrayBuffer()`. A duplicate file name gets a `-2` suffix.
- [ ] **Step 4: Run the tests to verify they pass**
- [ ] **Step 5: Commit**

### Task 5: Stage 1, the browser model in the Auto-label tool

**Files:**
- Modify: `src/lib/hooks/useAssistedLabelingTools/useAssistedLabelingTools.svelte.ts` (merged list, tool always available)
- Modify: `src/lib/components/SampleDetails/SampleDetailsToolbar/SampleDetailsToolbar.svelte:80` (`showLabelWithModelTool = isOnAssistedLabelingView`)
- Modify: `src/lib/components/SampleDetails/LabelWithModelOverlay/useLabelWithModel.svelte.ts` (browser branch in `generate`)
- Modify: `src/lib/components/SampleDetails/LabelWithModelPopUp/LabelWithModelPopUp.svelte` (groups, load-file item)
- Modify: `src/lib/components/SampleDetails/LabelWithModelPopUp/ModelRunControls/ModelRunControls.svelte` (download text)
- Test: `useLabelWithModel.svelte.test.ts`, `ModelRunControls/ModelRunControls.test.ts`

**Interfaces:**
- Consumes: `useBrowserModels`, `loadImageBitmap`.
- Produces: the merged model type `AutoLabelModel = LabelingModelView & { runsIn: 'browser' | 'server' }`. Browser models come first. `useLabelWithModel` params gain `modelRunsIn: 'browser' | 'server' | null`. `ModelRunControls` gains the prop `downloadProgress: { loaded: number; total: number } | null`.

- [ ] **Step 1: Write the failing tests**

```ts
// useLabelWithModel.svelte.test.ts (mock useBrowserModels and loadImageBitmap)
it('runs a browser model in the browser, not on the server', async () => {
    // params: modelId 'ltdetrv2-s-coco', modelRunsIn 'browser'; detector.detect resolves [personPreview]
    await hook.generate();
    expect(hook.predictions).toEqual([personPreview]);
    expect(mutateAsync).not.toHaveBeenCalled(); // the mocked server mutation
});
// ModelRunControls.test.ts (new, next to the component)
it('shows the download progress on the run button', () => {
    render(ModelRunControls, { ...defaultProps, downloadProgress: { loaded: 12e6, total: 20e6 } });
    expect(screen.getByText('Downloading model… 12 of 20 MB')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run them to verify they fail**, `npx vitest run src/lib/components/SampleDetails/LabelWithModel*`
- [ ] **Step 3: Implement**

The Select groups become `Browser · Object detection`, `Server · Object detection` and
`Server · Instance segmentation`; the `Select` component already renders groups. Add the item
`{ value: '__load_model_file__', label: 'Load model file (.onnx)…' }` to the browser group.
Picking it opens a hidden `<input type="file" accept=".onnx">`, calls `addModelFile`, and
selects the returned ID. The popup passes `$loadProgress` for the selected model down to
`ModelRunControls`.

- [ ] **Step 4: Run the tests to verify they pass, including the existing ones in these folders**
- [ ] **Step 5: Verify in the browser:** open an image, edit mode, Auto-label, run `ltdetrv2-s-coco`. Expected: download text on the first run, boxes in the overlay, Save works, and a Python-registered model still runs.
- [ ] **Step 6: Commit**

### Task 6: Batch runner

**Files:**
- Create: `lightly_studio_view/src/lib/components/BatchAutoLabel/runBatchAutoLabel.ts`
- Test: `lightly_studio_view/src/lib/components/BatchAutoLabel/runBatchAutoLabel.test.ts`

**Interfaces:**
- Produces: `runBatchAutoLabel(params: { sampleIds: string[]; detect: (sampleId: string) => Promise<ModelAnnotationPreview[]>; save: (sampleId: string, previews: ModelAnnotationPreview[]) => Promise<void>; classNames: Set<string>; signal: AbortSignal; onProgress: (progress: { done: number; annotationCount: number; failedCount: number }) => void }): Promise<{ done: number; annotationCount: number; failedSampleIds: string[] }>`

- [ ] **Step 1: Write the failing tests**

```ts
it('saves only ticked classes', ...)            // detect → [person, car], classNames {person} → save(id, [person])
it('skips saving an image with nothing kept but counts it done', ...)  // save not called, done 1
it('records a failed image and continues', ...) // detect rejects for 'b' of ['a','b','c'] → failedSampleIds ['b'], done 3
it('stops after the current image on abort', ...) // abort inside the first onProgress → save called once, done 1
```

- [ ] **Step 2: Run them to verify they fail**, `npx vitest run src/lib/components/BatchAutoLabel`
- [ ] **Step 3: Implement.** One image at a time; check `signal.aborted` before each image; call `onProgress` after each image.
- [ ] **Step 4: Run the tests to verify they pass**
- [ ] **Step 5: Commit**

### Task 7: Stage 2 UI, pill action, dialog and dock

**Files:**
- Create: `src/lib/components/BatchAutoLabel/useBatchAutoLabel.svelte.ts`
- Create: `src/lib/components/BatchAutoLabel/AutoLabelDialog/AutoLabelDialog.svelte`
- Create: `src/lib/components/BatchAutoLabel/AutoLabelDock/AutoLabelDock.svelte`
- Create: `src/lib/components/BatchAutoLabel/index.ts`
- Modify: `src/lib/components/SelectionPill/SelectionPill.svelte` (optional `onAutoLabel` prop)
- Modify: `src/routes/datasets/[dataset_id]/[collection_type]/[collection_id]/+layout.svelte:856` (wire it up for image collections)
- Test: `src/lib/components/SelectionPill/SelectionPill.test.ts`

**Interfaces:**
- Consumes: `runBatchAutoLabel`, `useBrowserModels`, `loadImageBitmap`, `useSaveAnnotationPreviews`, `useAnnotationCollections`, `useAnnotationCollectionsFilter`, `useGlobalStorage().getSelectedSampleIds`.
- Produces: `useBatchAutoLabel(params: { getCollectionId: () => string; getDatasetId: () => string }): { state: Readable<BatchState>; start(params: { sampleIds: string[]; modelId: string; threshold: number; classNames: string[] }): void; stop(): void }`,
  where `BatchState = { status: 'idle' | 'running' | 'finished' | 'stopped'; total: number; done: number; annotationCount: number; failedCount: number; modelId: string | null }`.

- [ ] **Step 1: Write the failing test**

```ts
it('shows Auto-label only when a handler is given, and calls it', async () => {
    const onAutoLabel = vi.fn();
    render(SelectionPill, { selectedCount: 3, onClear: vi.fn(), onAutoLabel });
    await userEvent.click(screen.getByRole('button', { name: 'Auto-label' }));
    expect(onAutoLabel).toHaveBeenCalledOnce();
});
it('hides Auto-label without a handler', () => {
    render(SelectionPill, { selectedCount: 3, onClear: vi.fn() });
    expect(screen.queryByRole('button', { name: 'Auto-label' })).toBeNull();
});
```

- [ ] **Step 2: Run it to verify it fails**, `npx vitest run src/lib/components/SelectionPill`
- [ ] **Step 3: Implement**
  - **Pill:** a `Sparkles` icon button labeled "Auto-label".
  - **`useBatchAutoLabel`:** wraps `runBatchAutoLabel` with an `AbortController`. Each save
    uses `saveAs: 'box'` and `annotationSource: modelId`, through `useSaveAnnotationPreviews`.
    Add a `beforeunload` listener while running, and call `stop()` on destroy, so leaving the
    collection stops the run.
  - **Dialog** (shadcn `Dialog`):
    1. Model `Select` over browser models.
    2. The existing `ThresholdInput`.
    3. A checklist of `class_names`, all ticked. On open it calls `getDetector` and shows
       `$loadProgress` while the classes load.
    4. A button labeled `Auto-label {n} images`.
  - **Dock** (fixed bottom-right):
    1. While running: `{done} of {total} · {annotationCount} annotations`, a progress bar, Stop,
       and "Keep this tab open".
    2. After the run: "View results", which looks up the source ID by name in
       `useAnnotationCollections` and calls `setSelectedCollectionIds([id])`. Plus a close
       button that resets the state to idle.
    3. If `failedCount > 0`: `{failedCount} images failed`.
- [ ] **Step 4: Run the tests to verify they pass, plus `make static-checks`**
- [ ] **Step 5: Commit**

### Task 8: End-to-end check

- [ ] **Step 1: Start the app** against a local dataset with `lightly_studio_view` on the dev server.
- [ ] **Step 2: Batch run:** select 50 images, Auto-label, keep all classes. Expected: the dock counts up, scrolling the grid stays usable, and "View results" filters to `ltdetrv2-s-coco`.
- [ ] **Step 3: Speed:** record ms per image on WebGPU and with `?ep=wasm` (Review Focus 4), and the first-load download time.
- [ ] **Step 4: Review Focus 3 and 5:** one very large image; close the tab mid-run (warning shown); open another collection mid-run (run stops, done images kept).
- [ ] **Step 5: Write the numbers and any jank** under a "Results" heading in the spec. If the grid janks, the next step is approach 2 (Web Worker).
- [ ] **Step 6: Commit**
