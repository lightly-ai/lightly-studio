import { getAllGroupsInfiniteOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createInfiniteQuery, useQueryClient } from '@tanstack/svelte-query';
import { derived, get, writable } from 'svelte/store';
import type { GroupView } from '$lib/api/lightly_studio_local/types.gen';
import { toReadable, type StoreOrVal } from '$lib/utils/reactiveParams';

/**
 * A Svelte hook for infinite scrolling of groups data with pagination support.
 *
 * This hook fetches groups for a collection using TanStack Query's infinite query pattern,
 * automatically managing pagination, caching, and loading states.
 *
 * @param collectionId - The ID of the collection to fetch groups for (plain value or readable store)
 *
 * @returns An object containing:
 * - `data`: Writable store containing all loaded GroupView items (flattened from all pages)
 * - `totalCount`: Writable store with the total number of groups available
 * - `query`: The underlying TanStack Query infinite query object with loading/error states
 * - `loadMore`: Function to load the next page of results
 * - `refresh`: Function to invalidate and refetch all data
 */
export const useGroupsInfinite = (collectionId: StoreOrVal<string>) => {
    const collectionIdStore = toReadable(collectionId);
    const optionsStore = derived(collectionIdStore, (currentCollectionId) => {
        const readGroupsOptions = getAllGroupsInfiniteOptions({
            query: { limit: 30 },
            body: {
                filter: {
                    sample_filter: {
                        collection_id: currentCollectionId
                    }
                }
            }
        });
        return {
            ...readGroupsOptions,
            getNextPageParam: (lastPage: { nextCursor?: number | null }) =>
                lastPage.nextCursor ?? undefined
        };
    });

    const query = createInfiniteQuery(optionsStore);

    const client = useQueryClient();
    const refresh = () => {
        client.invalidateQueries({ queryKey: get(optionsStore).queryKey });
    };

    const data = writable<GroupView[]>([]);
    const totalCount = writable(0);

    query.subscribe((query) => {
        if (query.isSuccess) {
            const groups = query.data.pages.flatMap((page) => page.data);
            data.set(groups);
            totalCount.set(query.data.pages[0].total_count);
        }
    });

    const loadMore = () => {
        const currentQuery = get(query);
        if (currentQuery.hasNextPage && !currentQuery.isFetchingNextPage) {
            currentQuery.fetchNextPage();
        }
    };

    return {
        data,
        loadMore,
        query: query,
        refresh,
        totalCount
    };
};
