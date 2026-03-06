import type { DimensionBounds } from '$lib/services/loadDimensionBounds';
import { loadDimensionBounds } from '$lib/services/loadDimensionBounds';
import { useSessionStorage } from '$lib/hooks/useSessionStorage/useSessionStorage';
import { isReadableStore } from '$lib/hooks/utils/isReadableStore';
import { derived, get, writable, type Readable } from 'svelte/store';

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
type CollectionIdInput = string | Readable<string> | undefined;

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

    if (get(lastCollectionId) !== collection_id) {
        return;
    }

    if (dimensionBoundsData) {
        dimensionsBounds.set(dimensionBoundsData);
        dimensionsValues.set(dimensionBoundsData);
    }
};

const bindCollectionLoader = <T>(source: Readable<T>, collectionId: CollectionIdInput) => {
    if (!collectionId) {
        return source;
    }

    if (!isReadableStore<string>(collectionId)) {
        loadInitialDimensionBounds(collectionId);
        return source;
    }

    return derived([source, collectionId], ([$source, $collectionId]) => {
        if ($collectionId) {
            loadInitialDimensionBounds($collectionId);
        }

        return $source;
    });
};

export const useDimensions = (collection_id?: CollectionIdInput) => {
    return {
        dimensionsBounds: bindCollectionLoader(dimensionsBounds, collection_id),
        dimensionsValues: bindCollectionLoader(dimensionsValues, collection_id),
        updateDimensionsValues,
        updateDimensionsBounds
    };
};
