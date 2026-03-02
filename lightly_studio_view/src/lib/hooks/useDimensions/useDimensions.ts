import type { DimensionBounds } from '$lib/services/loadDimensionBounds';
import { loadDimensionBounds } from '$lib/services/loadDimensionBounds';
import { useSessionStorage } from '$lib/hooks/useSessionStorage/useSessionStorage';
import { get, writable } from 'svelte/store';

const dimensionsBounds = useSessionStorage<DimensionBounds | null>(
    'lightlyStudio_dimensions_bounds',
    null
);

const dimensionsValues = useSessionStorage<DimensionBounds | null>(
    'lightlyStudio_dimensions_values',
    null
);

const updateDimensionsValues = (bounds: DimensionBounds) => {
    dimensionsValues.set(bounds);
};

const updateDimensionsBounds = (bounds: DimensionBounds) => {
    dimensionsBounds.set(bounds);
};
const lastCollectionId = writable<string | null>(null);

const loadInitialDimensionBounds = async (collection_id: string) => {
    if (get(lastCollectionId) === collection_id) {
        return;
    }

    lastCollectionId.set(collection_id);
    dimensionsBounds.set(null);
    dimensionsValues.set(null);

    const { data: dimensionBoundsData } = await loadDimensionBounds({
        collection_id: collection_id
    });

    if (dimensionBoundsData) {
        dimensionsBounds.set(dimensionBoundsData);
        dimensionsValues.set(dimensionBoundsData);
    }
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
