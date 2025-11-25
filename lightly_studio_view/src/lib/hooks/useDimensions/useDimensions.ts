import type { DimensionBounds } from '$lib/services/loadDimensionBounds';
import { loadDimensionBounds } from '$lib/services/loadDimensionBounds';
import { useSessionStorage } from '$lib/hooks/useSessionStorage/useSessionStorage';
import { get, writable } from 'svelte/store';
import { useRootDataset } from '../useRootDataset/useRootDataset';

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

const loadInitialDimensionBounds = async () => {
    if (get(isInitialized)) {
        return;
    }

    // Use the root dataset to load dimensions.
    const rootDataset = await useRootDataset();
    const { data: dimensionBoundsData } = await loadDimensionBounds({
        dataset_id: rootDataset.dataset_id
    });

    if (dimensionBoundsData) {
        dimensionsBounds.set(dimensionBoundsData);
        dimensionsValues.set(dimensionBoundsData);
    }

    isInitialized.set(true);
};

export const useDimensions = (dataset_id?: string) => {
    if (dataset_id) {
        loadInitialDimensionBounds();
    }

    return {
        dimensionsBounds,
        dimensionsValues,
        updateDimensionsValues,
        updateDimensionsBounds
    };
};
