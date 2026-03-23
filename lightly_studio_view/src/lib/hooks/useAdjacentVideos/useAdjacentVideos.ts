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
    const { videoFilter } = useVideoFilters();
    const { textEmbedding } = useGlobalStorage();

    const filter = get(videoFilter);
    return useAdjacentSamples({
        params: {
            sampleId,
            body: {
                sample_type: SampleType.VIDEO,
                filters: filter
                    ? { filter_type: 'video' as const, ...filter }
                    : {
                          filter_type: 'video' as const,
                          sample_filter: {
                              collection_id: collectionId
                          }
                      },
                text_embedding: get(textEmbedding)?.embedding
            }
        }
    });
};
