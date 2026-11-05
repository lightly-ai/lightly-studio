# Crop class prediction while annotating

Prototype. A popover for class choice is being built separately; this uses a plain strip
until it lands.

## Why

Annotators pick the class of every box by hand. The editor already knows what labeled crops
look like, so it can suggest the class of a new box from them.

## What the user gets

In the image editor, for a new bounding box or a new brush mask:

1. The annotation is created right away with the last-used class, as today. If no class was
   used yet, the class dialog still opens.
2. A strip under the toolbar shows a spinner and "Predicting class…".
3. When the prediction returns, the strip shows the top 3: `1 car 82% · 2 truck 11% · 3 bus 4%`.
   Pressing 1, 2 or 3 relabels the annotation. Doing nothing keeps the last-used class.
4. If no prediction is possible, the strip hides.

A brush stroke that extends a selected mask creates no annotation and predicts nothing.

## How it predicts

- **KNN** over the crop embeddings of other annotations in the same annotation collection and
  embedding model. k = 10.
- **Text anchors** for the cold start: one embedding of `"a photo of a {class}"` per class,
  when the model's space can embed text. The anchor stays in the vote after labels exist, so a
  class with no crops can still win, and real crops outvote it after a few labels.
- **Score** per class:

  ```text
  score(c) = Σ similarity of c's neighbours among the k nearest + λ · text_similarity(c)
  ```

  Scores are normalized to sum to 1. λ starts at 3, so one anchor is worth about one crop
  neighbour (crop-to-crop similarity is around 0.7–0.9, text-to-crop around 0.2–0.35). λ is an
  unmeasured guess; tune it on the manual test.
- Every crop the user leaves on the last-used class enters the pool with that class. Unfixed
  wrong labels pull later predictions toward it. Accepted for the prototype.

## Backend

**Route**, new file under `api/routes/api/annotations/`:

```text
POST /api/collections/{collection_id}/annotations/{annotation_id}/class_predictions
→ [{annotation_label_id, label_name, score}, ...]
```

Returns every class of the collection, sorted by score descending. Classes with no neighbour
and no anchor get 0. No `top_n` parameter: the frontend slices. Add it as an optional parameter
only if collections with thousands of classes appear.

**Service** `annotation_class_prediction_service`, one request:

1. Resolve the annotation collection's crop embedder with `default_embedder.resolve_default_embedder`
   and `ImageCropPathEmbedder`. This bootstraps the default model on the first call in a
   GUI-only project, as SDK ingest does. No embedder → `[]`.
2. Embed the annotation's crop and store it. Make `_embed_annotation_chunk` in
   `embed/embed_samples.py` public so ingest and prediction share it. Masks use the bounding box
   stored on `SegmentationAnnotationTable`.
3. KNN through a new annotation resolver: cosine distance with `db_vector.cosine_distance`,
   same annotation collection, same model, excluding this annotation. Returns label ID and
   similarity per row.
4. Text anchors through the registry's `TextEmbedder` for the model's space. Cache in memory by
   `(model_id, class name)`. No text embedder → no anchors.
5. Score as above.

The `few_shot_classifier` random forest is not reused: KNN has no training step, so each new
label counts on the next box.

## Frontend

- `ClassPredictionStrip`, mounted in `SampleDetailsPanel`. Shows the spinner, then the top 3.
- After `createObjectDetectionAnnotation` in `SampleObjectDetectionRect.svelte` and the
  create branch of `finishBrush` in `useSegmentationMaskBrush.ts`, call the predict route with
  the new annotation ID.
- Keys 1, 2, 3 relabel through `useUpdateAnnotationsMutation` and push an entry with
  `addAnnotationLabelChangeToUndoStack`, as the side panel does. They act only while the strip
  belongs to the selected annotation.
- The editor has no digit shortcuts today, so 1–3 are free.

## Errors

| Case | Backend | Strip |
|---|---|---|
| No crop embedder | `200 []` | hides |
| No text embedder and no labeled crops | `200 []` | hides |
| Box outside the image, or broken image | `200 []` | hides |
| Annotation not found | `404` | hides |
| Annotation is not a box or mask | `400` | never called |
| Remote embedder unavailable | existing error handler | hides |

If a second box is drawn before the first prediction returns, the late response is dropped.

## Testing

1. Resolver: KNN excludes the annotation itself, stays in its annotation collection, uses only
   its model.
2. Service, with a fake embedder returning fixed vectors: zero-shot only, KNN only, blended, no
   embedder → `[]`, every class returned including zeros.
3. Route: 404 and 400.
4. Frontend vitest: spinner then top 3; 1/2/3 call the update; a stale response is ignored.
5. Manual: draw boxes on the local COCO 10k subset. Record predict latency and how many labels
   per class it takes before KNN beats zero-shot.

## Out of scope

- Video, point-cloud cuboids, Smart Select, Find Instances, classification annotations.
- Auto-applying the top class.
- The popover.
- Persisting the text-anchor cache or tuning λ beyond the manual test.
