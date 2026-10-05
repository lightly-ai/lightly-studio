import { omit } from 'lodash-es';
import type { buildVideoFilter } from '$lib/hooks';

type VideoFilterParams = NonNullable<Parameters<typeof buildVideoFilter>[0]>;

// sample_ids and embedding_region are set externally (plot selection), not from the
// component's filter controls, so they are excluded from the base-params comparison and
// merged back instead of being overwritten.
export const paramsWithoutExternalFilters = (params: VideoFilterParams) => ({
    ...params,
    filters: params.filters ? omit(params.filters, ['sample_ids', 'embedding_region']) : undefined
});

// Merge the externally-set selection (sample_ids and embedding_region) from the previous
// filter params into the new base params. Keep the selection only when the collection matches
// because it belongs to a specific collection and must be dropped when navigating elsewhere.
export const mergeExternalFilters = (
    baseParams: VideoFilterParams,
    currentParams: VideoFilterParams | null
): VideoFilterParams => {
    if (currentParams?.collection_id !== baseParams.collection_id) {
        return baseParams;
    }
    const { sample_ids: sampleIds, embedding_region: embeddingRegion } =
        currentParams.filters ?? {};
    if (!sampleIds?.length && !embeddingRegion) {
        return baseParams;
    }
    return {
        ...baseParams,
        filters: {
            ...baseParams.filters,
            sample_ids: sampleIds?.length ? sampleIds : undefined,
            embedding_region: embeddingRegion
        }
    };
};
