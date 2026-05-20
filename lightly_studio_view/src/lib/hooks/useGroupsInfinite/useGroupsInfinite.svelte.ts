import { getAllGroupsInfiniteOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createInfiniteQuery, useQueryClient } from '@tanstack/svelte-query';
import { writable } from 'svelte/store';
import type { GroupView } from '$lib/api/lightly_studio_local/types.gen';
import { GRID_PAGE_SIZE } from '$lib/constants';

/**
 * A Svelte hook for infinite scrolling of groups data with pagination support.
 *
 * This hook fetches groups for a collection using TanStack Query's infinite query pattern,
 * automatically managing pagination, caching, and loading states.
 *
 * @param collection_id - The ID of the collection to fetch groups for
 *
 * @returns An object containing:
 * - `data`: Writable store containing all loaded GroupView items (flattened from all pages)
 * - `totalCount`: Writable store with the total number of groups available
 * - `query`: The underlying TanStack Query infinite query object with loading/error states
 * - `loadMore`: Function to load the next page of results
 * - `refresh`: Function to invalidate and refetch all data
 */
export const useGroupsInfinite = (getCollectionId: () => string) => {
    const query = createInfiniteQuery(() => ({
        ...getAllGroupsInfiniteOptions({
            path: { collection_id: getCollectionId() },
            query: { limit: GRID_PAGE_SIZE },
            body: {}
        }),
        getNextPageParam: (lastPage) => lastPage.nextCursor || undefined
    }));

    const client = useQueryClient();
    const refresh = () => {
        const options = getAllGroupsInfiniteOptions({
            path: { collection_id: getCollectionId() },
            query: { limit: GRID_PAGE_SIZE },
            body: {}
        });
        client.invalidateQueries({ queryKey: options.queryKey });
    };

    const data = writable<GroupView[]>([]);
    const totalCount = writable(0);

    $effect(() => {
        if (query.isSuccess) {
            const groups = query.data.pages.flatMap((page) => page.data);
            data.set(groups);
            totalCount.set(query.data.pages[0].total_count);
        }
    });

    const loadMore = () => {
        if (query.hasNextPage && !query.isFetchingNextPage) {
            query.fetchNextPage();
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
