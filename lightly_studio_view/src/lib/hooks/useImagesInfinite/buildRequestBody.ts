import type { ReadImagesRequest } from '$lib/api/lightly_studio_local';
import { createMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
import { GRID_PAGE_SIZE } from '$lib/constants';
import { getAnnotationsFilter } from './getAnnotationsFilter';
import type { ImagesInfiniteParams } from './types';

export const buildRequestBody = (
    params: ImagesInfiniteParams,
    pageParam: number
): ReadImagesRequest => {
    const baseBody: ReadImagesRequest = {
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
    };

    if (params.mode === 'classifier' && params.classifierSamples) {
        const allSampleIds = [
            ...params.classifierSamples.positiveSampleIds,
            ...params.classifierSamples.negativeSampleIds
        ];

        return {
            ...baseBody,
            sample_ids: allSampleIds
        };
    } else if (params.mode === 'normal' && params.filters) {
        return {
            ...baseBody,
            filters: {
                ...baseBody.filters,
                sample_filter: {
                    ...(baseBody.filters?.sample_filter ?? {}),
                    annotations_filter: getAnnotationsFilter(params.filters),
                    tag_ids: params.filters.tag_ids?.length ? params.filters.tag_ids : undefined,
                    sample_ids: params.filters.sample_ids?.length
                        ? params.filters.sample_ids
                        : undefined
                },
                // TODO(Malte, 10/2025): Share the width/height mapping with useImageFilters to avoid drift.
                width: params.filters.dimensions
                    ? {
                          min: params.filters.dimensions.min_width,
                          max: params.filters.dimensions.max_width
                      }
                    : undefined,
                height: params.filters.dimensions
                    ? {
                          min: params.filters.dimensions.min_height,
                          max: params.filters.dimensions.max_height
                      }
                    : undefined
            }
        };
    }

    return baseBody;
};
