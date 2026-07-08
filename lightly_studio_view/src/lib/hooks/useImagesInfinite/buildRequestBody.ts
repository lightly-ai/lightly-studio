import type { ReadImagesRequest } from '$lib/api/lightly_studio_local';
import { createMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
import { GRID_PAGE_SIZE } from '$lib/constants';
import { getAnnotationsFilter } from './getAnnotationsFilter';
import type { ClassifierSamples, ImagesInfiniteParams, NormalModeFilters } from './types';

const buildBaseBody = (params: ImagesInfiniteParams, pageParam: number): ReadImagesRequest => ({
    pagination: {
        offset: pageParam,
        limit: GRID_PAGE_SIZE
    },
    text_embedding: params.text_embedding,
    sort_by: params.sort_by ?? undefined,
    filters: {
        sample_filter: {
            query_expr: params.query_expr ?? undefined,
            metadata_filters: params.metadata_values
                ? createMetadataFilters(params.metadata_values)
                : undefined
        }
    }
});

const withClassifierSamples = (
    base: ReadImagesRequest,
    samples: ClassifierSamples
): ReadImagesRequest => ({
    ...base,
    sample_ids: [...samples.positiveSampleIds, ...samples.negativeSampleIds]
});

const withNormalFilters = (
    base: ReadImagesRequest,
    filters: NormalModeFilters
): ReadImagesRequest => ({
    ...base,
    filters: {
        ...base.filters,
        sample_filter: {
            ...(base.filters?.sample_filter ?? {}),
            annotations_filter: getAnnotationsFilter(filters),
            tag_ids: filters.tag_ids?.length ? filters.tag_ids : undefined,
            sample_ids: filters.sample_ids?.length ? filters.sample_ids : undefined,
            confusion_cell: filters.confusion_cell ?? undefined,
            // Lasso/rectangle selection sent as geometry; the backend resolves it to sample
            // ids server-side so the request body stays small at scale (see LIG-9903).
            embedding_region: filters.embedding_region ?? undefined
        },
        // TODO(Malte, 10/2025): Share the width/height mapping with useImageFilters to avoid drift.
        width: filters.dimensions
            ? { min: filters.dimensions.min_width, max: filters.dimensions.max_width }
            : undefined,
        height: filters.dimensions
            ? { min: filters.dimensions.min_height, max: filters.dimensions.max_height }
            : undefined
    }
});

export const buildRequestBody = (
    params: ImagesInfiniteParams,
    pageParam: number
): ReadImagesRequest => {
    const base = buildBaseBody(params, pageParam);

    if (params.mode === 'classifier' && params.classifierSamples) {
        return withClassifierSamples(base, params.classifierSamples);
    }

    if (params.mode === 'normal' && params.filters) {
        return withNormalFilters(base, params.filters);
    }

    return base;
};
