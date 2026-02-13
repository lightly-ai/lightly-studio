# API Refactoring Proposal: Hide Collection Hierarchy from Frontend

**Status:** Proposed
**Author:** kondrat@lightly.ai
**Date:** 2026-02-09
**Related Issues:** TBD

## Executive Summary

The current API exposes internal database structure (collection hierarchy) to the frontend through URLs and API contracts. This proposal suggests refactoring the API to use dataset-centric endpoints, keeping collection management as an internal implementation detail.

## Current State

### Problem: Backend Structure Leaks to Frontend

**Current URL Structure:**
```
/datasets/{dataset_id}/{collection_type}/{collection_id}/videos
/datasets/{dataset_id}/{collection_type}/{collection_id}/frames
/datasets/{dataset_id}/{collection_type}/{collection_id}/annotations
```

**Current API Endpoints:**
```
POST /collections/{collection_id}/images/list
GET  /collections/{collection_id}/video/
GET  /collections/{video_frame_collection_id}/frame
GET  /collections/{collection_id}/annotations
```

**Issues:**

1. **Exposed Internal Structure**: Frontend knows about `collection_id`, `parent_collection_id`, and the collection hierarchy
2. **Complex URLs**: URLs contain both `dataset_id` and `collection_id` (which are often the same for root collections)
3. **Tight Coupling**: Frontend logic is coupled to backend database schema
4. **Poor Abstraction**: Frontend must understand that:
   - Videos are in the root collection
   - Frames are in a child collection with `SampleType.VIDEO_FRAME`
   - Annotations are in another child collection
5. **Migration Risk**: Any change to collection structure requires frontend changes

**Evidence from Codebase:**

```typescript
// Frontend explicitly checks parent_collection_id
// File: lightly_studio_view/src/routes/+page.ts:10-11
const mostRecentRootDataset = data
    .filter((collection) => collection.parent_collection_id == null)
```

```typescript
// Frontend navigates using collection_id in URLs
// File: lightly_studio_view/src/lib/routes.ts:105-108
videos: (datasetId: string, collectionType: string, collectionId: string) =>
    `/datasets/${datasetId}/${collectionType}/${collectionId}/videos`,
frames: (datasetId: string, collectionType: string, collectionId: string) =>
    `/datasets/${datasetId}/${collectionType}/${collectionId}/frames`,
```

## Understanding the Backend Architecture

### Why Collections Exist

**Collection** is a hierarchical container that organizes samples by type. Key characteristics:

1. **Sample Base Table**: All data types (images, videos, frames, annotations) extend a common `Sample` table that provides:
   - Tags
   - Embeddings (for similarity search)
   - Metadata (key-value pairs)
   - Links to annotations and captions

2. **Type-Specific Tables**: Extend `Sample` with type-specific fields:
   - `ImageTable`: `width`, `height`, `file_name`, `file_path_abs`
   - `VideoTable`: `fps`, `duration_s`, `width`, `height`
   - `VideoFrameTable`: `frame_number`, `frame_timestamp_s`, `parent_sample_id`
   - `AnnotationBaseTable`: `annotation_type`, `annotation_label_id`, `parent_sample_id`

3. **Collection Hierarchy**: Organizes related samples:
   ```
   Root Collection (VIDEO samples)
   ├── video_frame (child collection for extracted frames)
   │   └── ANNOTATION (grandchild for frame annotations)
   └── ANNOTATION (child collection for video annotations)
   ```

### Why Hierarchy is Needed (Backend)

1. **Parent-Child Relationships**:
   - Video frames reference their parent video via `parent_sample_id`
   - Annotations reference their parent image/frame via `parent_sample_id`

2. **Type Isolation**: Different sample types live in separate collections for:
   - Type-specific queries (query only frames, not videos)
   - Scoped operations (delete all frames without touching videos)
   - Clean schema (each collection has homogeneous sample types)

3. **Collection-Level Operations**:
   - Compute embeddings for a specific collection
   - Tag operations scoped to collection
   - Deep copy entire dataset with all child collections

4. **Automatic Management**: `get_or_create_child_collection()` automatically creates child collections when needed

**Example from code:**
```python
# File: lightly_studio/src/lightly_studio/utils/video_annotations_helpers.py:166-167
frames_collection_id = collection_resolver.get_or_create_child_collection(
    session=session, collection_id=collection_id, sample_type=SampleType.VIDEO_FRAME
)
```

### Why This Should Stay Internal

The collection hierarchy is a **valid backend design choice** for:
- Database normalization
- Reusable query patterns
- Type safety
- Relationship management

However, it's an **implementation detail** that shouldn't affect the API contract.

## Proposed Solution

### New API Structure

**New URL Structure:**
```
/datasets/{dataset_id}/images
/datasets/{dataset_id}/videos
/datasets/{dataset_id}/frames
/datasets/{dataset_id}/annotations
/datasets/{dataset_id}/captions
```

**New API Endpoints:**
```
POST /datasets/{dataset_id}/images
POST /datasets/{dataset_id}/videos
POST /datasets/{dataset_id}/frames
GET  /datasets/{dataset_id}/annotations
GET  /datasets/{dataset_id}/captions
```

### Implementation Strategy

#### Step 1: Collection Resolution Layer

Add a helper function at the API layer:

```python
def _resolve_collection_for_sample_type(
    session: Session,
    dataset_id: UUID,
    sample_type: SampleType
) -> UUID:
    """
    Resolve the appropriate collection ID for a given dataset and sample type.

    This encapsulates the collection hierarchy logic:
    - For root sample types (IMAGE, VIDEO, GROUP): returns dataset_id
    - For child sample types (VIDEO_FRAME, ANNOTATION, CAPTION):
      finds or creates the appropriate child collection

    Args:
        session: Database session
        dataset_id: The root dataset/collection ID
        sample_type: The type of samples to query

    Returns:
        The collection_id to use for querying samples

    Raises:
        ValueError: If dataset doesn't exist or sample_type is invalid
    """
    # Verify dataset exists
    root_collection = collection_resolver.get_by_id(session, dataset_id)
    if root_collection is None:
        raise ValueError(f"Dataset with ID {dataset_id} not found")

    # If querying the root sample type, use the dataset_id directly
    if root_collection.sample_type == sample_type:
        return dataset_id

    # For child sample types, get or create the child collection
    return collection_resolver.get_or_create_child_collection(
        session=session,
        collection_id=dataset_id,
        sample_type=sample_type
    )
```

#### Step 2: Update API Endpoints

**Example: Videos**

```python
# File: lightly_studio/src/lightly_studio/api/routes/api/video.py

# NEW ENDPOINT
video_router_v2 = APIRouter(prefix="/datasets/{dataset_id}", tags=["video"])

@video_router_v2.post("/videos", response_model=VideoViewsWithCount)
def get_all_videos(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset ID")],
    pagination: Annotated[PaginatedWithCursor, Depends()],
    body: ReadVideosRequest,
) -> VideoViewsWithCount:
    """Retrieve videos for a dataset.

    The backend automatically resolves which collection contains videos.
    """
    # Resolve the collection internally
    collection_id = _resolve_collection_for_sample_type(
        session=session,
        dataset_id=dataset_id,
        sample_type=SampleType.VIDEO
    )

    # Use existing resolver logic (no changes needed)
    return video_resolver.get_all_by_collection_id(
        session=session,
        collection_id=collection_id,
        pagination=Paginated(offset=pagination.offset, limit=pagination.limit),
        filters=body.filter,
        text_embedding=body.text_embedding,
    )

# Keep old endpoint for backwards compatibility (deprecated)
@video_router.post("/", response_model=VideoViewsWithCount)
@deprecated("Use /datasets/{dataset_id}/videos instead")
def get_all_videos_old(...):
    # Keep existing implementation
    ...
```

**Example: Images**

```python
# File: lightly_studio/src/lightly_studio/api/routes/api/image.py

# NEW ENDPOINT
image_router_v2 = APIRouter(prefix="/datasets/{dataset_id}", tags=["image"])

@image_router_v2.post("/images", response_model=ImageViewsWithCount)
def read_images(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset ID")],
    body: ReadImagesRequest,
) -> ImageViewsWithCount:
    """Retrieve images for a dataset.

    The backend automatically resolves which collection contains images.
    """
    # Resolve the collection internally
    collection_id = _resolve_collection_for_sample_type(
        session=session,
        dataset_id=dataset_id,
        sample_type=SampleType.IMAGE
    )

    # Use existing resolver logic (no changes needed)
    result = image_resolver.get_all_by_collection_id(
        session=session,
        collection_id=collection_id,
        pagination=body.pagination,
        filters=body.filters,
        text_embedding=body.text_embedding,
        sample_ids=body.sample_ids,
    )

    # Transform to response format
    scores: list[float | None] = (
        list(result.similarity_scores) if result.similarity_scores else [None] * len(result.samples)
    )
    return ImageViewsWithCount(
        samples=[
            ImageView(
                file_name=image.file_name,
                file_path_abs=image.file_path_abs,
                width=image.width,
                height=image.height,
                sample_id=image.sample_id,
                sample=image.sample,
                similarity_score=score,
            )
            for image, score in zip(result.samples, scores, strict=True)
        ],
        total_count=result.total_count,
    )

# Keep old endpoint for backwards compatibility (deprecated)
@image_router.post("/images/list")
@deprecated("Use /datasets/{dataset_id}/images instead")
def read_images_old(...):
    # Keep existing implementation
    ...
```

**Example: Frames**

```python
# File: lightly_studio/src/lightly_studio/api/routes/api/frame.py

frame_router_v2 = APIRouter(prefix="/datasets/{dataset_id}", tags=["frame"])

@frame_router_v2.post("/frames", response_model=VideoFrameViewsWithCount)
def get_all_frames(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset ID")],
    body: ReadVideoFramesRequest,
    pagination: Annotated[PaginatedWithCursor, Depends()],
) -> VideoFrameViewsWithCount:
    """Retrieve video frames for a dataset.

    The backend automatically finds or creates the VIDEO_FRAME child collection.
    """
    # Resolve the frames collection internally
    collection_id = _resolve_collection_for_sample_type(
        session=session,
        dataset_id=dataset_id,
        sample_type=SampleType.VIDEO_FRAME
    )

    # Use existing resolver logic
    return video_frame_resolver.get_all_by_collection_id(
        session=session,
        collection_id=collection_id,
        pagination=Paginated(offset=pagination.offset, limit=pagination.limit),
        filters=body.filter,
    )
```

**Example: Annotations**

```python
# File: lightly_studio/src/lightly_studio/api/routes/api/annotation.py

annotations_router_v2 = APIRouter(prefix="/datasets/{dataset_id}", tags=["annotations"])

@annotations_router_v2.get("/annotations", response_model=AnnotationViewsWithCount)
def read_annotations(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset ID")],
    pagination: Annotated[PaginatedWithCursor, Depends()],
    annotation_label_ids: Annotated[list[UUID] | None, Query()] = None,
    tag_ids: Annotated[list[UUID] | None, Query()] = None,
) -> GetAllAnnotationsResult:
    """Retrieve annotations for a dataset.

    The backend automatically finds the ANNOTATION collection.
    """
    # Resolve the annotations collection internally
    collection_id = _resolve_collection_for_sample_type(
        session=session,
        dataset_id=dataset_id,
        sample_type=SampleType.ANNOTATION
    )

    # Use existing resolver logic
    return annotation_resolver.get_all(
        session=session,
        pagination=Paginated(offset=pagination.offset, limit=pagination.limit),
        collection_id=collection_id,
        annotation_label_ids=annotation_label_ids,
        tag_ids=tag_ids,
    )
```

#### Step 3: Update Frontend Routes

**New Frontend URL Structure:**

```typescript
// File: lightly_studio_view/src/lib/routes.ts

export const routes = {
    home: () => `/`,
    dataset: {
        home: (datasetId: string) => `/datasets/${datasetId}`,
        images: (datasetId: string) => `/datasets/${datasetId}/images`,
        videos: (datasetId: string) => `/datasets/${datasetId}/videos`,
        frames: (datasetId: string) => `/datasets/${datasetId}/frames`,
        annotations: (datasetId: string) => `/datasets/${datasetId}/annotations`,
        captions: (datasetId: string) => `/datasets/${datasetId}/captions`,

        imageDetails: (datasetId: string, sampleId: string, index?: number) => {
            const path = `/datasets/${datasetId}/images/${sampleId}`;
            return index === undefined ? path : `${path}?index=${index}`;
        },

        videoDetails: (datasetId: string, sampleId: string, index?: number) => {
            const path = `/datasets/${datasetId}/videos/${sampleId}`;
            return index === undefined ? path : `${path}?index=${index}`;
        },

        frameDetails: (datasetId: string, sampleId: string, index?: number) => {
            const path = `/datasets/${datasetId}/frames/${sampleId}`;
            return index === undefined ? path : `${path}?index=${index}`;
        },

        annotationDetails: (
            datasetId: string,
            sampleId: string,
            annotationId: string,
            annotationIndex: number
        ) => {
            return `/datasets/${datasetId}/annotations/${sampleId}/${annotationId}/${annotationIndex}`;
        },
    }
};
```

**Updated API Calls:**

```typescript
// Before: Images
const { data } = await readImages({
    path: { collection_id: collectionId },
    body: { filters, pagination }
});

// After: Images
const { data } = await readImages({
    path: { dataset_id: datasetId },
    body: { filters, pagination }
});

// Before: Videos
const { data } = await readVideos({
    path: { collection_id: collectionId }
});

// After: Videos
const { data } = await readVideos({
    path: { dataset_id: datasetId }
});

// Before: Frames
const { data } = await readFrames({
    path: { video_frame_collection_id: frameCollectionId }
});

// After: Frames
const { data } = await readFrames({
    path: { dataset_id: datasetId }
});
```

## Benefits

### 1. Clean Separation of Concerns

- **Frontend**: Works with logical entities (datasets, videos, frames)
- **Backend**: Manages internal structure (collections, hierarchy, relationships)

### 2. Simplified Frontend

**Before:**
```typescript
// Must track both dataset_id and collection_id
routeHelpers.toImages(datasetId, collectionType, collectionId)
routeHelpers.toVideos(datasetId, collectionType, collectionId)
routeHelpers.toFrames(datasetId, collectionType, collectionId)

// Must understand collection hierarchy
.filter((collection) => collection.parent_collection_id == null)

// Must resolve collection IDs for child types
const frameCollectionId = (videoData?.frame?.sample as SampleView)?.collection_id;

// API calls with collection_id
await readImages({ path: { collection_id: collectionId } })
await readVideos({ path: { collection_id: collectionId } })
await readFrames({ path: { video_frame_collection_id: frameCollectionId } })
```

**After:**
```typescript
// Just use dataset_id - simple and consistent
routeHelpers.toImages(datasetId)
routeHelpers.toVideos(datasetId)
routeHelpers.toFrames(datasetId)

// No need to understand hierarchy
// Backend handles it automatically

// API calls with dataset_id only
await readImages({ path: { dataset_id: datasetId } })
await readVideos({ path: { dataset_id: datasetId } })
await readFrames({ path: { dataset_id: datasetId } })
```

### 3. Better API Contracts

- **RESTful**: Resources are addressable by meaningful IDs (dataset, not internal collection)
- **Intuitive**: `/datasets/{id}/videos` is clearer than `/collections/{id}/video/`
- **Stable**: Internal refactoring doesn't break API

### 4. Future-Proof

If backend changes collection structure (e.g., different hierarchy, denormalization, sharding), frontend remains unaffected.

### 5. Easier Onboarding

New developers don't need to understand:
- What collections are
- Why there are two IDs in URLs
- How the hierarchy works
- When to use dataset_id vs collection_id

## Migration Path

### Phase 1: Add New Endpoints (Backwards Compatible)

1. Implement `_resolve_collection_for_sample_type()` helper
2. Create new v2 routers with `/datasets/{dataset_id}` prefix
3. Keep old endpoints with deprecation warnings
4. Document both APIs

### Phase 2: Migrate Frontend

1. Update URL structure to remove `collection_type` and `collection_id`
2. Update API calls to use `dataset_id` only
3. Remove `parent_collection_id` checks from frontend
4. Simplify route helpers

### Phase 3: Remove Old Endpoints

1. After sufficient transition period
2. Remove deprecated endpoints
3. Clean up old code

## Risks and Mitigations

### Risk: Breaking Changes

**Mitigation**: Keep old endpoints during transition period, use API versioning

### Risk: Performance

**Mitigation**: The `get_or_create_child_collection()` call is a single DB query with indexed lookup. Negligible overhead.

### Risk: Ambiguity

**Question**: What if a dataset has both image and video samples?

**Answer**: Each dataset has a single root sample type. The `_resolve_collection_for_sample_type()` validates this and returns the appropriate collection. If querying for a type that doesn't exist, it returns an empty result or creates the child collection as needed.

## Implementation Checklist

- [ ] Create `_resolve_collection_for_sample_type()` helper in a shared API utilities module
- [ ] Update video endpoints to use `/datasets/{dataset_id}/videos`
- [ ] Update frame endpoints to use `/datasets/{dataset_id}/frames`
- [ ] Update annotation endpoints to use `/datasets/{dataset_id}/annotations`
- [ ] Update image endpoints to use `/datasets/{dataset_id}/images`
- [ ] Update caption endpoints to use `/datasets/{dataset_id}/captions`
- [ ] Update metadata endpoints to use `/datasets/{dataset_id}/metadata`
- [ ] Update tag endpoints to use `/datasets/{dataset_id}/tags`
- [ ] Mark old endpoints as deprecated
- [ ] Update OpenAPI schema generation
- [ ] Update frontend TypeScript SDK
- [ ] Update frontend route structure
- [ ] Update all frontend API calls
- [ ] Update frontend tests
- [ ] Update documentation
- [ ] Create migration guide for API consumers
- [ ] After transition period, remove old endpoints

## Conclusion

This refactoring improves API design by hiding implementation details while maintaining all existing functionality. The backend collection hierarchy remains unchanged and continues to provide its benefits (type isolation, relationships, scoped operations). The only change is adding a thin resolution layer at the API boundary.

The result is a cleaner, more maintainable system where frontend and backend concerns are properly separated.
