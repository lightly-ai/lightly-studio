import { SampleType } from '$lib/api/lightly_studio_local';
import { get } from 'svelte/store';
import { useAdjacentSamples } from '../useAdjacentSamples/useAdjacentSamples';
import { useGlobalStorage } from '../useGlobalStorage';
import { useVideoFilters } from '../useVideoFilters/useVideoFilters';

export const useAdjacentVideos = ({
    sampleId,
    collectionId
}: {
    sampleId: string;
    collectionId: string;
}) => {
    const { videoFilter, videoSortBy } = useVideoFilters();
    const { textEmbedding } = useGlobalStorage();

    const filter = get(videoFilter);
    const embedding = get(textEmbedding);
    const sortBy = embedding ? undefined : (get(videoSortBy) ?? undefined);
    return useAdjacentSamples({
        params: {
            sampleId,
            body: {
                sample_type: SampleType.VIDEO,
                collection_id: collectionId,
                filters: filter
                    ? { filter_type: 'video' as const, ...filter }
                    : { filter_type: 'video' as const },
                text_embedding: embedding?.embedding,
                sort_by: sortBy
            }
        }
    });
};
