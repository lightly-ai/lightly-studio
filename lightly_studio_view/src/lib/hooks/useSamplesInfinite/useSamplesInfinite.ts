import type { InfiniteData } from '@tanstack/svelte-query';
import { createInfiniteQuery, infiniteQueryOptions, useQueryClient } from '@tanstack/svelte-query';
import type { ReadSamplesError, ReadSamplesResponse } from '$lib/api/lightly_studio_local';
import { readSamples, type ReadSamplesRequest } from '$lib/api/lightly_studio_local';
import type { DimensionBounds } from '$lib/services/loadDimensionBounds';
import { createMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
import type { MetadataValues } from '$lib/services/types';

// Define mode-aware parameter types.
interface ClassifierSamples {
    positiveSampleIds: string[];
    negativeSampleIds: string[];
}

interface NormalModeFilters {
    annotation_label_ids?: string[];
    tag_ids?: string[];
    dimensions?: DimensionBounds;
    sample_ids?: string[];
}

interface CommonFilters {
    metadata_values?: MetadataValues;
    text_embedding?: number[];
}

interface NormalModeParams {
    mode: 'normal';
    filters?: NormalModeFilters;
}

interface ClassifierModeParams {
    mode: 'classifier';
    classifierSamples?: ClassifierSamples;
}

export type SamplesInfiniteParams = {
    dataset_id: string;
} & (NormalModeParams | ClassifierModeParams) &
    CommonFilters;

type SamplesQueryKey = readonly [
    string,
    string,
    'normal' | 'classifier',
    NormalModeFilters | ClassifierSamples | undefined,
    {
        metadata_values?: MetadataValues;
        text_embedding?: number[];
    }
];

// Create infinite query options for samples with mode-aware logic.
const createSamplesInfiniteOptions = (params: SamplesInfiniteParams) => {
    // Build query key with intelligent structure to minimize refetches.
    const queryKey: SamplesQueryKey = [
        'readSamplesInfinite',
        params.dataset_id,
        params.mode,
        params.mode === 'normal' ? params.filters : params.classifierSamples,
        {
            metadata_values: params.metadata_values,
            text_embedding: params.text_embedding
        }
    ];

    return infiniteQueryOptions<
        ReadSamplesResponse,
        ReadSamplesError,
        InfiniteData<ReadSamplesResponse>,
        SamplesQueryKey,
        number
    >({
        queryKey,
        queryFn: async ({ pageParam = 0, signal }) => {
            const requestBody = buildRequestBody(params, pageParam);

            const { data } = await readSamples({
                path: { dataset_id: params.dataset_id },
                body: requestBody,
                signal,
                throwOnError: true
            });
            return data;
        },
        initialPageParam: 0,
        getNextPageParam: (lastPage) => lastPage.nextCursor ?? undefined,
        enabled: isQueryEnabled(params)
    });
};

const buildRequestBody = (params: SamplesInfiniteParams, pageParam: number): ReadSamplesRequest => {
    const baseBody: ReadSamplesRequest = {
        pagination: {
            offset: pageParam,
            limit: 100
        },
        text_embedding: params.text_embedding,
        filters: {
            metadata_filters: params.metadata_values
                ? createMetadataFilters(params.metadata_values)
                : undefined
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
                annotation_label_ids: params.filters.annotation_label_ids?.length
                    ? params.filters.annotation_label_ids
                    : undefined,
                tag_ids: params.filters.tag_ids?.length ? params.filters.tag_ids : undefined,
                // TODO(Malte, 10/2025): Share the width/height mapping with useSamplesFilters to avoid drift.
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
                    : undefined,
                sample_ids: params.filters.sample_ids?.length
                    ? params.filters.sample_ids
                    : undefined
            }
        };
    }

    return baseBody;
};

const isQueryEnabled = (params: SamplesInfiniteParams): boolean => {
    if (params.mode === 'classifier') {
        // For classifier mode, classifier samples need to exist (even if empty arrays)
        // This ensures the query runs and can show the empty state
        return Boolean(params.classifierSamples);
    }

    // Normal mode is always enabled (return all samples if no filters).
    return true;
};

export const useSamplesInfinite = (params: SamplesInfiniteParams) => {
    const samplesOptions = createSamplesInfiniteOptions(params);
    const samples = createInfiniteQuery(samplesOptions);
    const client = useQueryClient();

    const refresh = () => {
        client.invalidateQueries({ queryKey: samplesOptions.queryKey });
    };

    return {
        samples,
        refresh
    };
};
