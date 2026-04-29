import {
    getAnnotationSampleIds,
    getImageSampleIds,
    getVideoFrameSampleIds,
    getVideoSampleIds
} from '$lib/api/lightly_studio_local/sdk.gen';
import type { GridType } from '$lib/types';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
import { useVideoFilters, buildVideoFilter } from '$lib/hooks/useVideoFilters/useVideoFilters';
import { useFramesFilter } from '$lib/hooks/useFramesFilter/useFramesFilter';
import { getFrameFilter } from '$lib/hooks/useFramesFilter/frameFilter';
import { useSelectedAnnotationsFilter } from '$lib/hooks/useAnnotationsFilter/useAnnotationsFilter';
import { get } from 'svelte/store';
import { toast } from 'svelte-sonner';

export function useSelectAll(collectionId: string, gridType: GridType) {
    const { setAllSelectedSampleIds, setAllSelectedAnnotationCropIds } = useGlobalStorage();
    const { imageFilter } = useImageFilters();
    const { filterParams: videoFilterParams } = useVideoFilters();
    const { filterParams: frameFilterParams } = useFramesFilter();
    const { annotationFilter } = useSelectedAnnotationsFilter(collectionId);

    let isLoading = false;

    const handleSelectAll = async () => {
        if (isLoading) return;
        isLoading = true;

        const toastId = toast.loading('Selecting all samples...');

        try {
            let sampleIds: string[] = [];

            if (gridType === 'images') {
                const filter = get(imageFilter);
                const { data } = await getImageSampleIds({
                    path: { collection_id: collectionId },
                    body: { filters: filter }
                });
                sampleIds = data ?? [];
            } else if (gridType === 'videos') {
                const params = get(videoFilterParams);
                const filter = buildVideoFilter(params);
                const { data } = await getVideoSampleIds({
                    path: { collection_id: collectionId },
                    body: { filter }
                });
                sampleIds = data ?? [];
            } else if (gridType === 'video_frames') {
                const params = get(frameFilterParams);
                const filter = getFrameFilter(params);
                const { data } = await getVideoFrameSampleIds({
                    path: { video_frame_collection_id: collectionId },
                    body: { filter }
                });
                sampleIds = data ?? [];
            } else if (gridType === 'annotations') {
                const filter = get(annotationFilter);
                const { data } = await getAnnotationSampleIds({
                    path: { collection_id: collectionId },
                    body: { filters: filter }
                });
                sampleIds = data ?? [];
            }

            if (gridType === 'annotations') {
                setAllSelectedAnnotationCropIds(collectionId, new Set(sampleIds));
            } else {
                setAllSelectedSampleIds(collectionId, new Set(sampleIds));
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
