import { get } from 'svelte/store';
import { toast } from 'svelte-sonner';
import type { GridType } from '$lib/types';
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

export function useSelectAll(collectionId: string, gridType: GridType) {
    const { setAllSelectedSampleIds, setAllSelectedAnnotationCropIds } = useGlobalStorage();
    const { imageFilter } = useImageFilters();
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

    const handleSelectAll = async () => {
        if (isLoading) return;
        isLoading = true;

        const toastId = toast.loading('Selecting all samples...');

        try {
            const sampleIds = await fetchSampleIds();

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
