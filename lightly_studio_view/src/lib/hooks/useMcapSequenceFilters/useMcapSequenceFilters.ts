import { derived, get, writable } from 'svelte/store';
import type { McapSequenceFilter, SampleFilter } from '$lib/api/lightly_studio_local';

export type McapSequenceFilterParams = {
    collection_id: string;
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
 * Filter state of the MCAP sequence grid. The filter panel writes the selected tags here and
 * the grid reads the filter.
 */
export const useMcapSequenceFilters = () => {
    // Resets the filter when the grid shows another collection.
    const setCollectionId = (collectionId: string) => {
        if (get(filterParams)?.collection_id === collectionId) {
            return;
        }
        filterParams.set({ collection_id: collectionId });
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
        updateTagIds
    };
};
