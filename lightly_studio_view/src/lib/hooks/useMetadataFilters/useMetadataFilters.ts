import { getMetadataInfoOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery } from '@tanstack/svelte-query';
import { get, writable } from 'svelte/store';
import type { components } from '$lib/schema';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';

type MetadataInfo = components['schemas']['MetadataInfoView'];
type MetadataBounds = Record<string, { min: number; max: number }>;
type MetadataValues = Record<string, { min: number; max: number }>;

const lastDatasetId = writable<string | null>();

const loadInitialMetadataInfo = async (dataset_id: string) => {
    if (get(lastDatasetId) == dataset_id) {
        return;
    }

    const metadataOptions = getMetadataInfoOptions({
        path: {
            dataset_id: dataset_id
        }
    });

    const metadataQuery = createQuery(metadataOptions);

    // Subscribe to the query to get the data
    metadataQuery.subscribe((queryResult) => {
        if (queryResult.data) {
            const metadataInfoData = queryResult.data;
            const { updateMetadataBounds, updateMetadataValues, updateMetadataInfo } =
                useGlobalStorage();

            // Extract numerical metadata for bounds and values
            const bounds: MetadataBounds = {};
            const values: MetadataValues = {};

            metadataInfoData.forEach((info: MetadataInfo) => {
                if (info.type === 'integer' || info.type === 'float') {
                    if (info.min != null && info.max != null) {
                        bounds[info.name] = { min: info.min, max: info.max };
                        values[info.name] = { min: info.min, max: info.max };
                    }
                }
            });

            updateMetadataBounds(bounds);
            updateMetadataValues(values);
            updateMetadataInfo(metadataInfoData);
            lastDatasetId.set(dataset_id);
        }
    });
};

type MetadataFilter = components['schemas']['MetadataFilter'];

export const createMetadataFilters = (metadataValues: MetadataValues): MetadataFilter[] => {
    const filters: MetadataFilter[] = [];
    const { metadataBounds } = useGlobalStorage();

    for (const [key, range] of Object.entries(metadataValues)) {
        // Only create filters if the range is different from the full range
        // This assumes that the bounds are available to compare against
        const bounds = get(metadataBounds);
        const bound = bounds[key];

        if (bound) {
            // Add min filter if it's not at the minimum bound
            if (range.min > bound.min) {
                filters.push({
                    key,
                    value: range.min,
                    op: '>='
                });
            }

            // Add max filter if it's not at the maximum bound
            if (range.max < bound.max) {
                filters.push({
                    key,
                    value: range.max,
                    op: '<='
                });
            }
        }
    }
    return filters;
};

export const useMetadataFilters = (dataset_id?: string) => {
    if (dataset_id) {
        loadInitialMetadataInfo(dataset_id);
    }

    const {
        metadataBounds,
        metadataValues,
        metadataInfo,
        updateMetadataValues,
        updateMetadataBounds,
        updateMetadataInfo
    } = useGlobalStorage();

    return {
        metadataBounds,
        metadataValues,
        metadataInfo,
        updateMetadataValues,
        updateMetadataBounds,
        updateMetadataInfo,
        createMetadataFilters
    };
};
