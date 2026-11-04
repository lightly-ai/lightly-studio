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
    const { filterParams, mcapSequenceFilter } = useMcapSequenceFilters();
    const { textEmbedding } = useGlobalStorage();

    // The page can open without the grid, e.g. from the groups view, while the stored grid
    // filter still belongs to another collection.
    const isGridCollection = get(filterParams)?.collection_id === collectionId;
    const filter = isGridCollection ? get(mcapSequenceFilter) : null;
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
