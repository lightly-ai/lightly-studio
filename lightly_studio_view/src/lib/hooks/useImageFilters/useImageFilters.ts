import { derived, get, writable } from 'svelte/store';
import type { components } from '$lib/schema';
import { createMetadataFilters } from '../useMetadataFilters/useMetadataFilters';
import type { ImagesInfiniteParams } from '../useImagesInfinite/useImagesInfinite';
import type { DimensionBounds } from '$lib/services/loadDimensionBounds';

type ImageFilter = components['schemas']['ImageFilter'];
type SampleFilter = components['schemas']['SampleFilter'];

const filterParams = writable<ImagesInfiniteParams>({} as ImagesInfiniteParams);

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

const imageFilter = derived(filterParams, ($filterParams): ImageFilter | null => {
    if (!$filterParams?.dataset_id || !$filterParams?.mode) {
        return null;
    }

    if ($filterParams.mode === 'classifier') {
        return null;
    }

    const filters: ImageFilter = {};

    const { width, height } = extractDimensions($filterParams.filters?.dimensions);
    if (width) {
        filters.width = width;
    }
    if (height) {
        filters.height = height;
    }

    const sampleFilter: SampleFilter = {};
    const sampleIds = $filterParams.filters?.sample_ids;
    if (sampleIds && sampleIds.length > 0) {
        sampleFilter.sample_ids = sampleIds;
    }

    const annotationLabelIds = $filterParams.filters?.annotation_label_ids;
    if (annotationLabelIds && annotationLabelIds.length > 0) {
        sampleFilter.annotation_label_ids = annotationLabelIds;
    }

    const tagIds = $filterParams.filters?.tag_ids;
    if (tagIds && tagIds.length > 0) {
        sampleFilter.tag_ids = tagIds;
    }

    if ($filterParams.metadata_values) {
        const metadataFilters = createMetadataFilters($filterParams.metadata_values);
        if (metadataFilters.length > 0) {
            sampleFilter.metadata_filters = metadataFilters;
        }
    }

    if (Object.keys(sampleFilter).length > 0) {
        filters.sample_filter = sampleFilter;
    }

    return Object.keys(filters).length > 0 ? filters : null;
});

export const useImageFilters = () => {
    const updateFilterParams = (params: ImagesInfiniteParams) => {
        filterParams.set(params);
    };

    // updates only sample ids in the existing filter params
    const updateSampleIds = (sampleIds: string[]) => {
        const params: ImagesInfiniteParams = {
            ...get(filterParams)
        };

        if (params.mode !== 'normal') {
            return;
        }

        const newParams: ImagesInfiniteParams = {
            ...params,
            filters: {
                ...params.filters,
                sample_ids: sampleIds.length > 0 ? sampleIds : undefined
            }
        };

        filterParams.set(newParams);
    };

    return {
        filterParams,
        imageFilter,
        updateFilterParams,
        updateSampleIds
    };
};
