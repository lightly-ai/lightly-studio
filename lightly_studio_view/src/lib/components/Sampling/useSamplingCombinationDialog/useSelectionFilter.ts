import { get } from 'svelte/store';
import type { SamplingRequest } from '$lib/api/lightly_studio_local/types.gen';
import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
import { useMcapSequenceFilters } from '$lib/hooks/useMcapSequenceFilters/useMcapSequenceFilters';
import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';

export function useSelectionFilter(
    getIsVideoCollection: () => boolean,
    getIsSequenceCollection: () => boolean = () => false
) {
    const { imageFilter } = useImageFilters();
    const { videoFilter } = useVideoFilters();
    const { mcapSequenceFilter } = useMcapSequenceFilters();

    function buildSelectionFilter(): SamplingRequest['filter'] {
        if (getIsSequenceCollection()) {
            const f = get(mcapSequenceFilter);
            return f ? { ...f, filter_type: 'mcap_sequence' } : null;
        }
        if (getIsVideoCollection()) {
            const f = get(videoFilter);
            return f ? { ...f, filter_type: 'video' } : null;
        }
        const f = get(imageFilter);
        return f ? { ...f, filter_type: 'image' } : null;
    }

    return { buildSelectionFilter };
}
