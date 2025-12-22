import type { DimensionBounds } from '$lib/services/loadDimensionBounds';
import { loadDimensionBounds } from '$lib/services/loadDimensionBounds';
import { useSessionStorage } from '$lib/hooks/useSessionStorage/useSessionStorage';
import { get, writable } from 'svelte/store';

const dimensionsBounds = useSessionStorage<DimensionBounds>('lightlyStudio_dimensions_bounds', {
    min_width: 0,
    max_width: 0,
    min_height: 0,
    max_height: 0
});

const dimensionsValues = useSessionStorage<DimensionBounds>('lightlyStudio_dimensions_values', {
    min_width: 0,
    max_width: 0,
    min_height: 0,
    max_height: 0
});

const updateDimensionsValues = (bounds: DimensionBounds) => {
    dimensionsValues.set(bounds);
};

const updateDimensionsBounds = (bounds: DimensionBounds) => {
    dimensionsBounds.set(bounds);
};
const isInitialized = writable(false as boolean);

const loadInitialDimensionBounds = async (collection_id: string) => {
    if (get(isInitialized)) {
        return;
    }

    const { data: dimensionBoundsData } = await loadDimensionBounds({
        collection_id: collection_id
    });

    if (dimensionBoundsData) {
        dimensionsBounds.set(dimensionBoundsData);
        dimensionsValues.set(dimensionBoundsData);
    }

    isInitialized.set(true);
};

export const useDimensions = (collection_id?: string) => {
    if (collection_id) {
        loadInitialDimensionBounds(collection_id);
    }

    return {
        dimensionsBounds,
        dimensionsValues,
        updateDimensionsValues,
        updateDimensionsBounds
    };
};
