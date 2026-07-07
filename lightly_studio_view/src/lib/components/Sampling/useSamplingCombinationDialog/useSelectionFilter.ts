import { get } from 'svelte/store';
import type { SamplingRequest } from '$lib/api/lightly_studio_local/types.gen';
import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';

export function useSelectionFilter(getIsVideoCollection: () => boolean) {
    const { imageFilter } = useImageFilters();
    const { videoFilter } = useVideoFilters();

    function buildSelectionFilter(): SamplingRequest['filter'] {
        if (getIsVideoCollection()) {
            const f = get(videoFilter);
            return f ? { ...f, filter_type: 'video' } : null;
        }
        const f = get(imageFilter);
        return f ? { ...f, filter_type: 'image' } : null;
    }

    return { buildSelectionFilter };
}
