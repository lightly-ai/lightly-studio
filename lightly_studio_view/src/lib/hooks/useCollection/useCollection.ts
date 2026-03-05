import { readCollectionOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { readCollectionHierarchyOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery, useQueryClient } from '@tanstack/svelte-query';
import { derived, get } from 'svelte/store';
import type { CollectionView } from '$lib/api/lightly_studio_local';
import { toReadable, type StoreOrVal } from '$lib/utils/reactiveParams';

type UseCollectionParams = {
    collectionId: string;
};

/**
 * Hook to fetch a single collection without children.
 * Use this for most cases where you only need the collection data.
 */
export const useCollection = (params: StoreOrVal<UseCollectionParams>) => {
    const paramsStore = toReadable(params);
    const optionsStore = derived(paramsStore, (currentParams) =>
        readCollectionOptions({ path: { collection_id: currentParams.collectionId } })
    );
    const client = useQueryClient();

    const collectionQuery = createQuery(optionsStore);

    const refetch = () => {
        client.invalidateQueries({ queryKey: get(optionsStore).queryKey });
    };

    return {
        collection: collectionQuery,
        refetch
    };
};

/**
 * Hook to fetch a collection with its full hierarchy (including all children).
 * Use this when you need the root collection with all child collections populated
 * (e.g., for navigation menus that need to show all available collections).
 */
export const useCollectionWithChildren = (params: StoreOrVal<UseCollectionParams>) => {
    const paramsStore = toReadable(params);
    const optionsStore = derived(paramsStore, (currentParams) =>
        readCollectionHierarchyOptions({ path: { collection_id: currentParams.collectionId } })
    );
    const client = useQueryClient();

    const hierarchyQuery = createQuery(optionsStore);

    // readCollectionHierarchy returns an array starting from the root
    // We need to get the first item (root collection) which has all children
    const collection = derived(hierarchyQuery, ($query) => {
        if (
            $query.isSuccess &&
            $query.data &&
            Array.isArray($query.data) &&
            $query.data.length > 0
        ) {
            // Return a new query-like object with the root collection
            return {
                ...$query,
                data: $query.data[0] as CollectionView // First item is the root collection with children
            };
        }
        return $query;
    });

    const refetch = () => {
        client.invalidateQueries({ queryKey: get(optionsStore).queryKey });
    };

    return {
        collection,
        refetch
    };
};
