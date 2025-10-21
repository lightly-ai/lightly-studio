import { derived, writable } from 'svelte/store';
import type { components } from '$lib/schema';
import { createMetadataFilters } from '../useMetadataFilters/useMetadataFilters';
import type { SamplesInfiniteParams } from '../useSamplesInfinite/useSamplesInfinite';
import type { DimensionBounds } from '$lib/services/loadDimensionBounds';

type SampleFilter = components['schemas']['SampleFilter'];

const filterParams = writable<SamplesInfiniteParams>({} as SamplesInfiniteParams);

const buildFilterDimensions = (min?: number, max?: number) => {
    if (min == null && max == null) {
        return undefined;
    }
    return {
        min: min ?? undefined,
        max: max ?? undefined
    };
};

const extractDimensions = (dimensions?: DimensionBounds) => {
    if (!dimensions) {
        return {};
    }

    const width = buildFilterDimensions(dimensions.min_width, dimensions.max_width);
    const height = buildFilterDimensions(dimensions.min_height, dimensions.max_height);

    return {
        width,
        height
    };
};

const sampleFilter = derived(filterParams, ($filterParams): SampleFilter | null => {
    if (!$filterParams?.dataset_id || !$filterParams?.mode) {
        return null;
    }

    if ($filterParams.mode === 'classifier') {
        return null;
    }

    const filters: SampleFilter = {};

    const { width, height } = extractDimensions($filterParams.filters?.dimensions);
    if (width) {
        filters.width = width;
    }
    if (height) {
        filters.height = height;
    }

    const sampleIds = $filterParams.filters?.sample_ids;
    if (sampleIds && sampleIds.length > 0) {
        filters.sample_ids = sampleIds;
    }

    const annotationLabelIds = $filterParams.filters?.annotation_label_ids;
    if (annotationLabelIds && annotationLabelIds.length > 0) {
        filters.annotation_label_ids = annotationLabelIds;
    }

    const tagIds = $filterParams.filters?.tag_ids;
    if (tagIds && tagIds.length > 0) {
        filters.tag_ids = tagIds;
    }

    if ($filterParams.metadata_values) {
        const metadataFilters = createMetadataFilters($filterParams.metadata_values);
        if (metadataFilters.length > 0) {
            filters.metadata_filters = metadataFilters;
        }
    }

    return Object.keys(filters).length > 0 ? filters : null;
});

export const useSamplesFilters = () => {
    const updateFilterParams = (params: SamplesInfiniteParams) => {
        filterParams.set(params);
    };
    return {
        filterParams,
        sampleFilter,
        updateFilterParams
    };
};
