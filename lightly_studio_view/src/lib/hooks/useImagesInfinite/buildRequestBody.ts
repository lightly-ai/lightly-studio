import type { ReadImagesRequest } from '$lib/api/lightly_studio_local';
import { GRID_PAGE_SIZE } from '$lib/constants';
import { buildSampleFilter, dimensionRanges, toMetadataFilters } from '$lib/utils/gridFilter';
import type { ImagesInfiniteParams } from './types';

export const buildRequestBody = (
    params: ImagesInfiniteParams,
    pageParam: number
): ReadImagesRequest => {
    const f = params.mode === 'normal' ? (params.filters ?? {}) : {};
    const classifierSamples = params.mode === 'classifier' ? params.classifierSamples : undefined;

    return {
        pagination: {
            offset: pageParam,
            limit: GRID_PAGE_SIZE
        },
        text_embedding: params.text_embedding,
        sort_by: params.sort_by ?? undefined,
        ...(classifierSamples && {
            sample_ids: [
                ...classifierSamples.positiveSampleIds,
                ...classifierSamples.negativeSampleIds
            ]
        }),
        filters: {
            ...dimensionRanges(f.dimensions),
            sample_filter: buildSampleFilter({
                sample_ids: f.sample_ids,
                tag_ids: f.tag_ids,
                annotation_label_ids: f.annotation_label_ids,
                annotation_collection_ids: f.collection_ids,
                confusion_cell: f.confusion_cell,
                // Lasso/rectangle selection sent as geometry; the backend resolves it to sample
                // ids server-side so the request body stays small at scale (see LIG-9903).
                embedding_region: f.embedding_region,
                query_expr: params.query_expr,
                metadata_filters: toMetadataFilters(
                    params.metadata_values,
                    params.categorical_metadata_values
                )
            })
        }
    };
};
