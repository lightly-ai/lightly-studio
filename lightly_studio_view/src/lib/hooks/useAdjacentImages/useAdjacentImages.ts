import { SampleType } from '$lib/api/lightly_studio_local';
import { get } from 'svelte/store';
import { useAdjacentSamples } from '../useAdjacentSamples/useAdjacentSamples';
import { useImageFilters } from '../useImageFilters/useImageFilters';
import { useGlobalStorage } from '../useGlobalStorage';

export const useAdjacentImages = ({ sampleId }: { sampleId: string }) => {
    const { imageFilter } = useImageFilters();
    const { textEmbedding } = useGlobalStorage();

    return useAdjacentSamples({
        params: {
            sampleId,
            body: {
                sample_type: SampleType.IMAGE,
                filters: get(imageFilter)!,
                text_embedding: get(textEmbedding)?.embedding
            }
        }
    });
};
