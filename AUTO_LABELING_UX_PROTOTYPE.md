# Auto- & AI-Assisted Labeling — UX Prototype: Decision Record

Author: Jonas · Date: 2026-09-11 · Status: proposed, for review

Scope of this record: the **UX** of auto-labeling and AI-assisted labeling, as a throwaway
prototype. Derived from the *Design: Auto- & ML-Assisted Labeling* doc, which owns the wire
protocol, hosting, and QA. Where this record contradicts that doc, it is because the prototype
is deliberately narrower — not because the doc is wrong.

Phase 2 (training loop) is a separate session and carries nothing forward from here.

---

## 1. What this prototype is for

| | |
|---|---|
| **Question it answers** | Can a first-class UI beat the plugins path, and is the batch run loop legible end to end? |
| **Control group** | `examples/coco_plugins_demo/lightly_train_inference_operator.py` driven through `OperatorDialog.svelte` — a working auto-labeling operator that exists today. |
| **Throughput** | Judged qualitatively (label 10 images by hand vs with the wand), not measured. |
| **Explicitly not under test** | Synchronous execution. Accepted as-is; we iterate later. |
| **Vehicle** | Throwaway branch of the real Studio app. Real grid, real editor, real samples. The code is written to be deleted. |
| **Model** | SAM 3, served locally, out of band. Serving is not part of this work. |
| **Deliverable** | This record, then implementation. |

## 2. Decisions

### Frame

| # | Decision | Why |
|---|---|---|
| 1 | Talk to the model **through the Studio backend** for both modes, using the protocol as specified. | The prototype's most valuable byproduct is finding where the wire contract hurts. Browser-direct hides exactly that. |
| 2 | Keep the Studio side **thin**: one router module, no `remote_service` table, endpoint from an env var. | Registry and hosting are other docs. A throwaway must not grow a schema. |
| 3 | **Images only.** | `VideoFrameTable` has no file path — frames are virtual and decoded from the parent video by pts. The existing inference operator restricts itself to `OperatorScope.IMAGE` for the same reason. Video is a materially different prototype. |
| 4 | Support only the **three annotation types that exist**: `CLASSIFICATION`, `SEGMENTATION_MASK`, `OBJECT_DETECTION`. | The data model has no keypoints or polylines, and captions are a separate table with no `confidence`. Instances are already native — each segmentation annotation carries its own bbox + mask, so SAM 3's instance output maps cleanly. Semantic masks have no home. |

### Auto-labeling (batch)

| # | Decision | Why |
|---|---|---|
| 5 | Entry point: `Header/Menu.svelte` + a `useAutoLabelDialog` hook + lazy mount in `MenuDialogHost.svelte`. **Filter-scoped.** | Mirrors Sampling and Export exactly. The filter panel expresses "these samples" better than a hand-made selection, and the design doc's model is filter-scoped throughout. Registering it as an operator instead would answer "can we beat plugins?" with "we didn't try." |
| 6 | Targets: **one free-text field**, each entry used as both prompt and annotation class, with a disclosure to override the class per prompt. | `prompt == class_name` is the 90% case ("classes of interest"); making users type `dog` twice is the friction this prototype exists to remove. The override matters for the interesting open-vocab case (`"person on a bicycle"` → `cyclist`). |
| 7 | The form states that **N targets ≈ N model calls per image**. | The targets field is quietly a cost multiplier. |
| 8 | A **required task toggle**: Object detection *or* Segmentation. One annotation type written per run. | SAM 3 returns masks and boxes are derivable, so this is purely "what do we persist". Writing both into one source renders every object twice, and no filter in the app separates types *within* a source. |
| 9 | Every run writes a **new auto-named annotation source** (`model + task + timestamp`), never appends. | A batch run is a bulk artifact you may want to delete wholesale. Isolation is the safety net. |
| 10 | **Asymmetry, deliberate**: assisted labeling keeps writing to whatever `AnnotationSourcePill.svelte` says. | An assisted click is the user labeling by hand, faster — those annotations belong with the rest of their work, not in a model-named source. Called out because a reviewer will otherwise read it as an inconsistency. |
| 11 | Show the model/endpoint as a **read-only line**, with a **pre-flight `ready`/`describe` check that blocks the run**. | Prevents the dominant failure mode: the local server is down and the user finds out inside an uncancellable modal. `describe` is also what tells the UI this model is open-vocab, so the call is needed anyway. |
| 12 | On completion, **always a summary dialog**: annotations created, images processed, images skipped, prompts that matched nothing, destination source name. | A toast cannot tell the user *where the results went* — and with auto-named sources (9) that is information they do not otherwise have. "Matched nothing" gets top billing: with open-vocab prompts a typo is the most likely failure and is indistinguishable from success in a toast. |
| 13 | Closing the dialog navigates to the **image grid filtered to the new source**. No run-scoped panel. | The grid *is* the review surface; every tool for looking at results already lives there. |

### Confidence

| # | Decision | Why |
|---|---|---|
| 14 | A **client-side confidence slider** in the left filter panel, next to `AnnotationCollectionsMenu` and `LabelsMenu`. | Annotation visibility in this app is *already* client-side — `SampleDetailsAnnotationSegment.svelte` keeps an `annotationsIdsToHide` set seeded from the source selection, and server-side pruning of the annotation payload exists for no dimension at all. So this is idiomatic, not a shortcut. `confidence` is already in the API payloads, the generated TS types, and the on-image label. |
| 15 | Plus a **write-time floor** in the run config. | SAM 3 returns many sub-0.1 detections; a 200-image run could otherwise write six figures of noise the slider merely hides. |
| 16 | The record states plainly: **hidden ≠ absent.** Export sees everything written. | This will otherwise bite someone at export time. |

### AI-assisted labeling — the wand

| # | Decision | Why |
|---|---|---|
| 17 | A fifth member of `ToolbarStatus`. **Wand icon, labelled "Smart select."** | "Magic brush" is not a brush, and sitting next to the real Brush it invites confusion. Reserve "brush" for the thing that paints. |
| 18 | Points are **positive, plus negative via modifier-click**. | Positive-only breaks on the first over-segmented result ("it grabbed the whole person, I wanted the shirt") with no recourse but starting over. Negative points are the difference between a toy and a tool. |
| 19 | **Enter infers once** over all placed points. No inference per click. | Simpler, and one model call per intent rather than per click. |
| 20 | Points render **instantly**; no spinner; the mask appears when it lands; stale responses are discarded by **sequence number**. | Instant points are what make it feel responsive while the mask lags. A spinner over a fast local call is worse than nothing. Out-of-order responses are the bug that makes the tool feel haunted. |
| 21 | A **per-call latency readout** in the prototype UI. | This is the throughput evidence we actually came for. It comes out before ship. |
| 22 | **Enter advances**: infer → uncommitted preview → Enter commits → Esc discards → adding a point and pressing Enter re-infers. Commit produces **one** undo entry. | The preview step is non-negotiable: commit runs `applySegmentationMaskConstraints` → `removeOverlapFromOtherSegmentationAnnotations`, which **carves pixels out of neighbouring masks**, backed out only via `restoreOverriddenSegmentationAnnotationsForUndo`. Infer-and-commit would make every refinement a write/unwrite cycle mutating other annotations — slow, and the likeliest place to corrupt masks. |
| 23 | Output type (Mask/Box) chosen in a **popover on the wand button**, defaulting to last used via `useGlobalStorage`. Switching re-derives from the same points. | Same shape as `BrushToolPopUp`. The points are the user's intent; the type is only the output shape, so a switch should feel free. |

### Deleting a run

| # | Decision | Why |
|---|---|---|
| 24 | A **row action in `AnnotationCollectionsMenu`**, with a confirm dialog naming the source and its annotation count. | That list is where a user already thinks about sources. |
| 25 | Available for **any** source, not just model-generated ones. | No provenance exists to distinguish them (the design doc defers it). This makes the confirm dialog the real safety feature — the action sits next to the user's ground-truth source. |
| 26 | **Fix the cascade** and `annotation_collection_coverage` cleanup. | `DELETE /collections/{collection_id}` is a bare `session.delete` today: no annotation cascade, no coverage cleanup. Shipping on it leaves orphaned annotation samples and stale coverage, and after three prompt-tuning runs the dataset's stats stop matching the screen — discrediting the prototype for reasons unrelated to its UX. |

### Naming

Glossary mandates **annotation class** (never "label"), **annotation source**, **labeling**. It has no
entry yet for these modes. Proposed additions: **auto-labeling** (batch; menu item *Auto-label…*) and
**AI-assisted labeling** (interactive).

## 3. Work this implies

The prototype is throwaway but not free. Ordered by risk.

**Backend**
- The repo's **first inference HTTP client** — no `httpx`, no wire models, no URL validation exists anywhere in `lightly_studio` today. Mirror `EmbeddingResult.kept_indices` for per-image failures.
- `/api/annotate/*` routes for batch and interactive, plus a `describe`/`ready` proxy for the pre-flight check.
- **Full-resolution row-major RLE → bbox-cropped int array** conversion at the Studio boundary (see risks).
- Delete-by-source: resolver + endpoint + annotation cascade + coverage cleanup.
- Write path: `annotation_resolver.create_many(..., collection_name=...)`, which get-or-creates the source. Not the REST create path.
- Scope resolution: `grid_filter_sample_ids.build_sample_ids_query(session, collection_id, grid_filter)`.

**Frontend**
- `ToolbarStatus` gains `'wand'`: the union in `contexts/SampleDetailsToolbar.svelte.ts`, a `WandToolbarButton`, a branch in the toolbar `$effect`, a render branch in `SampleDetailsImageContainer.svelte`, and the type popover.
- Point overlay, Enter/Esc handling, preview mask via `useSegmentationMaskPreview` + `canvasMaskManager`, commit through `applySegmentationMaskConstraints` with one `useReversibleActions` entry.
- `AutoLabelDialog` (model it on `Sampling/SamplingCombinationDialog.svelte`) + the summary dialog.
- Confidence filter item, copied from `CombinedMetadataDimensionsFilters/MetadataFilterItem/` (already does float bounds + tick quantization on `ui/slider`).
- Delete action + confirm in `AnnotationCollectionsMenu`.

## 4. Risks and gaps — named, not solved

| Risk | Note |
|---|---|
| **Mask representation mismatch** | `SegmentationAnnotationTable.segmentation_mask` is an int array in a **bbox-cropped** frame. The protocol specifies full-resolution row-major RLE. The conversion is ours, and the friction is a finding to send back to the protocol doc. |
| **No redo** | `useReversibleActions` is LIFO, capped at 50, undo-only. Shapes decision 22. |
| **No provenance** | Model-generated and hand-made sources are indistinguishable in the UI. Shapes decision 25. |
| **hidden ≠ absent** | Sub-threshold annotations are written and exported. Mitigated but not removed by the write-time floor. |
| **Sync, no cancel, no progress** | Accepted. Today's pattern is `PluginExecutingOverlay.svelte` — a blocking modal reading "Plugin executing. This might take up to several minutes…". No `ui/progress` primitive exists and `refetchInterval` appears nowhere in the frontend. |
| **Cost multiplier** | N targets ≈ N calls per image. Surfaced in the form, not enforced. |
| **"Was 0.5 right?"** | The first question a user asks on seeing results. The slider answers it for visibility; it does not answer it for what was written. Expect pressure for a destructive prune — that belongs in the QA doc. |

## 5. Out of scope

Superpixel · QA / review workflow · NMS or merging runs · job history · async jobs · progress and
cancel · model registry and its UI · provenance · captions, keypoints, polygons, semantic
segmentation · video and video frames · training (phase 2) · model hosting and serving.
