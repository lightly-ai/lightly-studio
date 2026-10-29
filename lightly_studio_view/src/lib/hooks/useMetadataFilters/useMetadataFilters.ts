import { getMetadataInfo } from '$lib/api/lightly_studio_local';
import type { MetadataInfoView, MetadataFilter } from '$lib/api/lightly_studio_local';
import { get, writable } from 'svelte/store';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { validate as validateUUID } from 'uuid';
import type { CategoricalMetadataValues } from '$lib/services/types';
type MetadataBounds = Record<string, { min: number; max: number }>;
type MetadataValues = Record<string, { min: number; max: number }>;

type CollectionMetadataFilters = {
    values: MetadataValues;
    categoricalValues: CategoricalMetadataValues;
};

const lastCollectionId = writable<string | null>(null);
// The collection whose filters the metadata stores hold, set once its info has loaded.
let loadedCollectionId: string | null = null;
// Filters of the collections the user left, so each tab gets its own back for the session.
const filtersByCollection = new Map<string, CollectionMetadataFilters>();

const loadInitialMetadataInfo = async (collection_id: string) => {
    if (get(lastCollectionId) === collection_id) {
        return;
    }
    if (!validateUUID(collection_id)) {
        return;
    }
    lastCollectionId.set(collection_id);
    const storage = useGlobalStorage();
    if (loadedCollectionId) {
        filtersByCollection.set(loadedCollectionId, {
            values: get(storage.metadataValues),
            categoricalValues: get(storage.categoricalMetadataValues)
        });
    }

    const { data: metadataInfoData } = await getMetadataInfo({
        path: {
            collection_id
        }
    });

    if (!metadataInfoData || get(lastCollectionId) !== collection_id) {
        return;
    }
    const {
        updateMetadataBounds,
        updateMetadataValues,
        updateCategoricalMetadataValues,
        updateMetadataInfo
    } = storage;

    // Extract numerical metadata for bounds and values
    const bounds: MetadataBounds = {};
    const values: MetadataValues = {};

    metadataInfoData.forEach((info: MetadataInfoView) => {
        if (info.type === 'integer' || info.type === 'float') {
            if (info.min != null && info.max != null) {
                bounds[info.name] = { min: info.min, max: info.max };
                values[info.name] = { min: info.min, max: info.max };
            }
        }
    });

    const saved = filtersByCollection.get(collection_id);
    updateMetadataBounds(bounds);
    updateMetadataValues(saved?.values ?? values);
    // On the first load, keep the categorical filters restored from session storage.
    if (loadedCollectionId) {
        updateCategoricalMetadataValues(saved?.categoricalValues ?? {});
    }
    updateMetadataInfo(metadataInfoData);
    loadedCollectionId = collection_id;
};

export const createMetadataFilters = (
    metadataValues: MetadataValues,
    categoricalMetadataValues: CategoricalMetadataValues = {}
): MetadataFilter[] => {
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
    for (const [key, values] of Object.entries(categoricalMetadataValues)) {
        if (values.length > 0) {
            filters.push({ key, value: values, op: 'in' });
        }
    }
    return filters;
};

export const useMetadataFilters = (collection_id?: string) => {
    if (collection_id) {
        loadInitialMetadataInfo(collection_id);
    }

    const {
        metadataBounds,
        metadataValues,
        metadataInfo,
        categoricalMetadataValues,
        updateMetadataValues,
        updateCategoricalMetadataValues,
        updateMetadataBounds,
        updateMetadataInfo
    } = useGlobalStorage();

    return {
        metadataBounds,
        metadataValues,
        metadataInfo,
        categoricalMetadataValues,
        updateMetadataValues,
        updateCategoricalMetadataValues,
        updateMetadataBounds,
        updateMetadataInfo,
        createMetadataFilters
    };
};
