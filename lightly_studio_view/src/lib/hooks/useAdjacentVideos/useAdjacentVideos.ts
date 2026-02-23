import { SampleType } from '$lib/api/lightly_studio_local';
import { get } from 'svelte/store';
import { useAdjacentSamples } from '../useAdjacentSamples/useAdjacentSamples';
import { useGlobalStorage } from '../useGlobalStorage';
import { useVideoFilters } from '../useVideoFilters/useVideoFilters';

export const useAdjacentVideos = ({ sampleId }: { sampleId: string }) => {
    const { videoFilter } = useVideoFilters();
    const { textEmbedding } = useGlobalStorage();

    return useAdjacentSamples({
        params: {
            sampleId,
            body: {
                sample_type: SampleType.VIDEO,
                filters: get(videoFilter) ?? {},
                text_embedding: get(textEmbedding)?.embedding
            }
        }
    });
};
