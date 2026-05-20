import { readCollectionOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { readCollectionHierarchyOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery, useQueryClient } from '@tanstack/svelte-query';
import type { CollectionView } from '$lib/api/lightly_studio_local';

/**
 * Hook to fetch a single collection without children.
 * Use this for most cases where you only need the collection data.
 */
export const useCollection = ({ collectionId }: { collectionId: string }) => {
    const options = readCollectionOptions({ path: { collection_id: collectionId } });
    const client = useQueryClient();

    const collectionQuery = createQuery(() => options);

    const refetch = () => {
        client.invalidateQueries({ queryKey: options.queryKey });
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
export const useCollectionWithChildren = ({ collectionId }: { collectionId: string }) => {
    const options = readCollectionHierarchyOptions({ path: { collection_id: collectionId } });
    const client = useQueryClient();

    const hierarchyQuery = createQuery(() => options);

    // readCollectionHierarchy returns an array starting from the root
    // We need to get the first item (root collection) which has all children
    const collection = new Proxy(hierarchyQuery, {
        get(target, property, receiver) {
            if (property === 'data') {
                return target.isSuccess && Array.isArray(target.data) && target.data.length > 0
                    ? (target.data[0] as CollectionView)
                    : undefined;
            }

            return Reflect.get(target, property, receiver);
        }
    }) as typeof hierarchyQuery & { data: CollectionView | undefined };

    const refetch = () => {
        client.invalidateQueries({ queryKey: options.queryKey });
    };

    return {
        collection,
        refetch
    };
};
