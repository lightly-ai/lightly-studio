# STU-21: One Shared Grid Filter Builder

**Issue:** STU-21. **Base:** `michal-stu-23-operator-scope-label-says-filtered-when-no`, which has the STU-22, STU-24 and STU-23 fixes.

## Why

Four functions build the backend filter. Each one has its own copy of the same steps, and the copies drifted apart. The drift caused STU-22 and STU-23. STU-22 already deleted `buildImageFilter`. These four are left, with their eslint `complexity`:

| Complexity | Function |
| -- | -- |
| 32 | `buildVideoFilter` |
| 31 | `imageFilter` derived in `useImageFilters` |
| 25 | `getFrameFilter` |
| 11 | `withNormalFilters` in `buildRequestBody` |

## Goals

- Write each step once: drop empty lists, build the annotations filter, convert ranges, and add `sample_filter` only when it has content.
- Bring all four functions to a complexity of 10 or less, and close the width/height TODO in `buildRequestBody.ts`.
- Let the setters share one patch helper: `updateSampleIds`, `updateEmbeddingRegion` and `updateConfusionCell` in the image hook, and the first two in the video hook.
- Move `withFilterOverrides` next to the builder, merge `imageDimensionRanges` into the shared range helper, and simplify how `sample_filter` is handled.

## Constraints

- **The backend gets the same JSON, with two exceptions.** `buildRequestBody` stops sending `metadata_filters: []` and an empty `sample_filter: {}`. The ticket says the backend treats both as "no filter".
- **Pin the output first.** Before a function changes, its PR adds tests that pin its current output for every field. The tests compare the JSON form, so an `undefined` value and a missing key count as equal, the same as on the wire.
- **Public hook APIs, stores and params types stay the same.**
- **The image and video filters still always return a filter object.** The "return `null` when empty" check never fires, so it is removed. STU-23 already stopped relying on it.
- **The count filters change only their imports.** This includes `buildVideoFrameAnnotationCountsFilter`.

## Design

The helpers go in a new folder, `$lib/utils/gridFilter/`, named after the backend `GridFilter` union:

- **`buildSampleFilter(parts)`** takes the optional sample IDs, tag IDs, annotation label and collection IDs, plot selection, confusion cell, metadata filters and query. It drops empty lists and missing values. It builds `annotations_filter` with `getAnnotationsFilter`, which moves here, so an empty annotations filter is never sent. It passes `embedding_region` through unchanged. It returns `undefined` when nothing is set.
- **`toRange(range)`** gives `undefined` for a missing range. Otherwise it gives `{ min, max }`, with `null` turned into `undefined`. It is used for width, height and frame number. `fps` and `duration_s` are `FloatRange` values and pass through unchanged.
- **`dimensionRanges(bounds)`** gives `{ width, height }`. It replaces the three copies of this conversion, including `imageDimensionRanges`. The old empty checks differ (`!== undefined` and `== null`). For an empty collection the backend returns `{}` at runtime, so the filter sends `width: {}` and `height: {}`. The backend treats an empty range as no filter.
- **`buildGridFilter(filterType, fields, sampleFilter)`** builds the typed grid filter: `ImageFilter`, `VideoFilter` or `VideoFrameFilter`. It leaves out `undefined` fields, and adds `sample_filter` only when it is defined.
- **`withFilterOverrides`** moves here.
  - A `sample_filter` override is always applied key by key. No caller sets `sample_filter: undefined` to remove the whole thing, so that special case goes away.
  - It removes `undefined` keys and an empty `sample_filter`, but it does not use `buildSampleFilter`. This keeps the `metadata_filters: []` that the count filters send today. (My call.)
- **`patchFilters(params, patch)`** merges `patch` into `params.filters`. Each setter keeps its own guard: images need `mode === 'normal'`, and videos need `collection_id`.

With these helpers, `imageFilter`, `buildVideoFilter` and `getFrameFilter` only collect their parts and call `buildGridFilter`. The frame filter still always sets `frame_number`, and sets it to `{}` when there are no bounds. `buildRequestBody` has no `filter_type`, so it calls `buildSampleFilter` and `dimensionRanges` directly.

## PRs

The PRs are stacked on the base branch:

1. `michal-stu-21-share-one-samplefilter-builder-across-image`: add the shared builder helpers.
2. `michal-stu-21-image-filter-builder`: build `imageFilter` in `useImageFilters` with the builder.
3. `michal-stu-21-request-body-builder`: build the image request body with the builder, and close the TODO.
4. `michal-stu-21-video-frame-filter-builder`: build `buildVideoFilter` and `getFrameFilter` with the builder.
5. `michal-stu-21-filter-patch-helper`: use `patchFilters` in the setters, and simplify `withFilterOverrides`.

## Left to the builder

The file names, the exact `parts` type, the test names, and whether `buildGridFilter` and `withFilterOverrides` share a private helper.
