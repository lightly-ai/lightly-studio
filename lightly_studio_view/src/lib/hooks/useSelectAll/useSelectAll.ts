import { get } from 'svelte/store';
import { toast } from 'svelte-sonner';
import type { GridType } from '$lib/types';
import type { TagByFilterBody } from '$lib/api/lightly_studio_local';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
import { useVideoFilters, buildVideoFilter } from '$lib/hooks/useVideoFilters/useVideoFilters';
import { useFramesFilter } from '$lib/hooks/useFramesFilter/useFramesFilter';
import { getFrameFilter } from '$lib/hooks/useFramesFilter/frameFilter';
import { useSelectedAnnotationsFilter } from '$lib/hooks/useAnnotationsFilter/useAnnotationsFilter';
import { fetchSampleIdsForImages } from './fetchSampleIdsForImages';
import { fetchSampleIdsForVideos } from './fetchSampleIdsForVideos';
import { fetchSampleIdsForVideoFrames } from './fetchSampleIdsForVideoFrames';
import { fetchSampleIdsForAnnotations } from './fetchSampleIdsForAnnotations';

type SnapshotFilter = TagByFilterBody['filter'];

/** Discriminator for each by-filter-taggable grid, used to normalize a no-condition select-all. */
const GRID_FILTER_TYPE = {
    images: 'image',
    videos: 'video',
    video_frames: 'video_frame',
    annotations: 'annotations'
} as const satisfies Partial<Record<GridType, SnapshotFilter['filter_type']>>;

export function useSelectAll(collectionId: string, gridType: GridType) {
    const {
        setAllSelectedSampleIds,
        setAllSelectedAnnotationCropIds,
        setSelectAllSnapshot,
        setSelectAllAnnotationSnapshot,
        clearSelectAllSnapshot,
        clearSelectAllAnnotationSnapshot
    } = useGlobalStorage();
    const { imageFilter, filterParams: imageFilterParams } = useImageFilters();
    const { filterParams: videoFilterParams } = useVideoFilters();
    const { filterParams: frameFilterParams } = useFramesFilter();
    const { annotationFilter } = useSelectedAnnotationsFilter(collectionId);

    let isLoading = false;

    /**
     * Resolve this grid's filter once, returning both the ID fetch and the filter to snapshot. The
     * raw filter is captured synchronously (the `fetchIds` thunk closes over it), so the fetch and
     * the snapshot can't diverge if the user changes the filter mid-fetch. `snapshotFilter` is
     * `null` to force the ID path; otherwise an empty filter is normalized to a conditionless typed
     * one. The `as` casts bridge the builders' optional `filter_type` to the union's required
     * discriminant, sound because every builder stamps it at runtime.
     */
    const resolveGrid = (): {
        snapshotFilter: SnapshotFilter | null;
        fetchIds: () => Promise<string[]>;
    } => {
        switch (gridType) {
            case 'images': {
                const filter = get(imageFilter);
                // A null image filter in classifier mode is selection-driven, not "no conditions";
                // a conditionless filter would tag every image, so force the ID path.
                const snapshotFilter =
                    get(imageFilterParams).mode === 'classifier'
                        ? null
                        : ((filter as SnapshotFilter | null) ?? {
                              filter_type: GRID_FILTER_TYPE.images
                          });
                return {
                    snapshotFilter,
                    fetchIds: () => fetchSampleIdsForImages(collectionId, filter)
                };
            }
            case 'videos': {
                const filter = buildVideoFilter(get(videoFilterParams));
                return {
                    snapshotFilter: (filter as SnapshotFilter | null) ?? {
                        filter_type: GRID_FILTER_TYPE.videos
                    },
                    fetchIds: () => fetchSampleIdsForVideos(collectionId, filter)
                };
            }
            case 'video_frames': {
                const filter = getFrameFilter(get(frameFilterParams));
                return {
                    snapshotFilter: (filter as SnapshotFilter | null) ?? {
                        filter_type: GRID_FILTER_TYPE.video_frames
                    },
                    fetchIds: () => fetchSampleIdsForVideoFrames(collectionId, filter)
                };
            }
            case 'annotations': {
                const filter = get(annotationFilter);
                return {
                    snapshotFilter: (filter as SnapshotFilter | undefined) ?? {
                        filter_type: GRID_FILTER_TYPE.annotations
                    },
                    fetchIds: () => fetchSampleIdsForAnnotations(collectionId, filter)
                };
            }
            default:
                return { snapshotFilter: null, fetchIds: () => Promise.resolve([]) };
        }
    };

    const handleSelectAll = async () => {
        if (isLoading) return;
        isLoading = true;

        const toastId = toast.loading('Selecting all samples...');

        try {
            const { snapshotFilter, fetchIds } = resolveGrid();
            const sampleIds = await fetchIds();
            const isAnnotation = gridType === 'annotations';

            if (isAnnotation) {
                setAllSelectedAnnotationCropIds(collectionId, new Set(sampleIds));
            } else {
                setAllSelectedSampleIds(collectionId, new Set(sampleIds));
            }

            // `setAll…` never invalidates, so set or clear the snapshot here explicitly. A `null`
            // filter (e.g. classifier mode) must *clear* a prior snapshot, not leave it stale — only
            // a later manual edit invalidates otherwise.
            const setSnapshot = isAnnotation
                ? setSelectAllAnnotationSnapshot
                : setSelectAllSnapshot;
            const clearSnapshot = isAnnotation
                ? clearSelectAllAnnotationSnapshot
                : clearSelectAllSnapshot;
            if (snapshotFilter !== null) {
                setSnapshot(collectionId, { filter: snapshotFilter, size: sampleIds.length });
            } else {
                clearSnapshot(collectionId);
            }

            toast.success(`${sampleIds.length} samples selected`, { id: toastId });
        } catch {
            toast.error('Failed to select all samples', { id: toastId });
        } finally {
            isLoading = false;
        }
    };

    return { handleSelectAll };
}
