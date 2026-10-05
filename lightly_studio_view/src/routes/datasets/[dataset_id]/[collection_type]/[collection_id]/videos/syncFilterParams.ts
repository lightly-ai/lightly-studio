import { omit } from 'lodash-es';
import type { buildVideoFilter } from '$lib/hooks';

type VideoFilterParams = NonNullable<Parameters<typeof buildVideoFilter>[0]>;

export const paramsWithoutExternalFilters = (params: VideoFilterParams) => ({
    ...params,
    filters: params.filters ? omit(params.filters, ['sample_ids', 'embedding_region']) : undefined
});

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
