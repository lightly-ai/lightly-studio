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

/** Payload the by-filter tag endpoint accepts: a `filter_type`-discriminated union of grid filters. */
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
        setSelectAllAnnotationSnapshot
    } = useGlobalStorage();
    const { imageFilter, filterParams: imageFilterParams } = useImageFilters();
    const { filterParams: videoFilterParams } = useVideoFilters();
    const { filterParams: frameFilterParams } = useFramesFilter();
    const { annotationFilter } = useSelectedAnnotationsFilter(collectionId);

    let isLoading = false;

    const fetchSampleIds = async (): Promise<string[]> => {
        switch (gridType) {
            case 'images':
                return fetchSampleIdsForImages(collectionId, get(imageFilter));
            case 'videos':
                return fetchSampleIdsForVideos(
                    collectionId,
                    buildVideoFilter(get(videoFilterParams))
                );
            case 'video_frames':
                return fetchSampleIdsForVideoFrames(
                    collectionId,
                    getFrameFilter(get(frameFilterParams))
                );
            case 'annotations':
                return fetchSampleIdsForAnnotations(collectionId, get(annotationFilter));
            default:
                return [];
        }
    };

    /**
     * Resolve the filter to tag this select-all by. Read synchronously before `fetchSampleIds`, so
     * the snapshot can't capture a filter the user changed mid-fetch. Returns `null` to force the
     * ID path. The `as` casts bridge the builders' optional `filter_type` to the required
     * discriminant, sound because every builder stamps it at runtime.
     */
    const captureSnapshotFilter = (): SnapshotFilter | null => {
        switch (gridType) {
            case 'images': {
                // A null image filter in classifier mode is selection-driven, not "no conditions";
                // a conditionless filter would tag every image, so force the ID path.
                if (get(imageFilterParams).mode === 'classifier') {
                    return null;
                }
                return (
                    (get(imageFilter) as SnapshotFilter | null) ?? {
                        filter_type: GRID_FILTER_TYPE.images
                    }
                );
            }
            case 'videos':
                return (
                    (buildVideoFilter(get(videoFilterParams)) as SnapshotFilter | null) ?? {
                        filter_type: GRID_FILTER_TYPE.videos
                    }
                );
            case 'video_frames':
                return (
                    (getFrameFilter(get(frameFilterParams)) as SnapshotFilter | null) ?? {
                        filter_type: GRID_FILTER_TYPE.video_frames
                    }
                );
            case 'annotations':
                return (
                    (get(annotationFilter) as SnapshotFilter | undefined) ?? {
                        filter_type: GRID_FILTER_TYPE.annotations
                    }
                );
            default:
                return null;
        }
    };

    const handleSelectAll = async () => {
        if (isLoading) return;
        isLoading = true;

        const toastId = toast.loading('Selecting all samples...');

        try {
            const snapshotFilter = captureSnapshotFilter();
            const sampleIds = await fetchSampleIds();
            const isAnnotation = gridType === 'annotations';

            if (isAnnotation) {
                setAllSelectedAnnotationCropIds(collectionId, new Set(sampleIds));
            } else {
                setAllSelectedSampleIds(collectionId, new Set(sampleIds));
            }

            // Written after `setAll…` (which never invalidates), so only a later manual edit nulls
            // it. `null` here means "use the ID path" (e.g. classifier mode).
            if (snapshotFilter !== null) {
                const snapshot = { filter: snapshotFilter, size: sampleIds.length };
                if (isAnnotation) {
                    setSelectAllAnnotationSnapshot(collectionId, snapshot);
                } else {
                    setSelectAllSnapshot(collectionId, snapshot);
                }
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
