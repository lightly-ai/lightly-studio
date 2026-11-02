import { SampleType } from '$lib/api/lightly_studio_local';
import { get } from 'svelte/store';
import { useAdjacentSamples } from '../useAdjacentSamples/useAdjacentSamples';
import { useGlobalStorage } from '../useGlobalStorage';
import { useMcapSequenceFilters } from '../useMcapSequenceFilters/useMcapSequenceFilters';

/** Previous/next MCAP sequence in the order of the sequences grid, with its filters and text search. */
export const useAdjacentMcapSequences = ({
    sampleId,
    collectionId
}: {
    sampleId: string;
    collectionId: string;
}) => {
    const { mcapSequenceFilter } = useMcapSequenceFilters();
    const { textEmbedding } = useGlobalStorage();

    const filter = get(mcapSequenceFilter);
    const embedding = get(textEmbedding);
    return useAdjacentSamples({
        params: {
            sampleId,
            body: {
                sample_type: SampleType.SEQUENCE,
                collection_id: collectionId,
                filters: filter ? { ...filter, filter_type: 'mcap_sequence' } : undefined,
                text_embedding: embedding?.embedding
            }
        }
    });
};
