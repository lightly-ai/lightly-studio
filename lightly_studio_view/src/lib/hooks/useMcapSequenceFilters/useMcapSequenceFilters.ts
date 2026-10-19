import { derived, get, writable } from 'svelte/store';
import type {
    EmbeddingRegion,
    McapSequenceFilter,
    SampleFilter
} from '$lib/api/lightly_studio_local';

export type McapSequenceFilterParams = {
    collection_id: string;
    sample_ids?: string[];
    embedding_region?: EmbeddingRegion;
    tag_ids?: string[];
};

const filterParams = writable<McapSequenceFilterParams | null>(null);

export const buildMcapSequenceFilter = (
    params: McapSequenceFilterParams | null
): McapSequenceFilter | null => {
    if (!params?.collection_id) {
        return null;
    }

    const sampleFilter: SampleFilter = {};
    if (params.sample_ids && params.sample_ids.length > 0) {
        sampleFilter.sample_ids = params.sample_ids;
    }
    if (params.embedding_region) {
        sampleFilter.embedding_region = params.embedding_region;
    }
    if (params.tag_ids && params.tag_ids.length > 0) {
        sampleFilter.tag_ids = params.tag_ids;
    }

    const filter: McapSequenceFilter = { filter_type: 'mcap_sequence' };
    if (Object.keys(sampleFilter).length > 0) {
        filter.sample_filter = sampleFilter;
    }
    return filter;
};

const mcapSequenceFilter = derived(filterParams, ($filterParams) =>
    buildMcapSequenceFilter($filterParams)
);

/**
 * Filter state of the MCAP sequence grid. The filter panel writes the selected tags and the
 * embedding plot writes the selected region here. The grid, sampling and plot read the filter.
 */
export const useMcapSequenceFilters = () => {
    // Resets the filter when the grid shows another collection.
    const setCollectionId = (collectionId: string) => {
        if (get(filterParams)?.collection_id === collectionId) {
            return;
        }
        filterParams.set({ collection_id: collectionId });
    };

    const updateSampleIds = (sampleIds: string[]) => {
        const params = get(filterParams);
        if (!params) {
            return;
        }
        filterParams.set({
            ...params,
            sample_ids: sampleIds.length > 0 ? sampleIds : undefined
        });
    };

    const updateEmbeddingRegion = (embeddingRegion: EmbeddingRegion | null) => {
        const params = get(filterParams);
        if (!params) {
            return;
        }
        filterParams.set({ ...params, embedding_region: embeddingRegion ?? undefined });
    };

    const updateTagIds = (tagIds: string[]) => {
        const params = get(filterParams);
        if (!params) {
            return;
        }
        filterParams.set({ ...params, tag_ids: tagIds.length > 0 ? tagIds : undefined });
    };

    return {
        filterParams,
        mcapSequenceFilter,
        setCollectionId,
        updateSampleIds,
        updateEmbeddingRegion,
        updateTagIds
    };
};
