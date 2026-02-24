import { getAllGroupsInfiniteOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createInfiniteQuery, useQueryClient } from '@tanstack/svelte-query';
import { get, writable } from 'svelte/store';
import type { GroupView } from '$lib/api/lightly_studio_local/types.gen';

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
 *
 * @example
 * ```svelte
 * <script>
 *   import { useGroupsInfinite } from '$lib/hooks/useGroups/useGroupsInfinite';
 *
 *   const collectionId = 'my-collection-id';
 *   const { data, totalCount, query, loadMore, refresh } = useGroupsInfinite(collectionId);
 * </script>
 *
 * {#if $query.isLoading}
 *   <p>Loading groups...</p>
 * {:else if $query.isError}
 *   <p>Error: {$query.error.message}</p>
 * {:else}
 *   <div>
 *     <h2>Total groups: {$totalCount}</h2>
 *     {#each $data as group}
 *       <div>{group.name}</div>
 *     {/each}
 *
 *     {#if $query.hasNextPage}
 *       <button on:click={loadMore} disabled={$query.isFetchingNextPage}>
 *         {$query.isFetchingNextPage ? 'Loading...' : 'Load More'}
 *       </button>
 *     {/if}
 *
 *     <button on:click={refresh}>Refresh</button>
 *   </div>
 * {/if}
 * ```
 *
 * @example
 * ```svelte
 * <!-- Infinite scroll example -->
 * <script>
 *   import { useGroupsInfinite } from '$lib/hooks/useGroupsInfinite';
 *   import { onMount } from 'svelte';
 *
 *   const { data, query, loadMore } = useGroupsInfinite('collection-123');
 *
 *   onMount(() => {
 *     const handleScroll = () => {
 *       const scrolledToBottom = window.innerHeight + window.scrollY >= document.body.offsetHeight - 100;
 *       if (scrolledToBottom && $query.hasNextPage && !$query.isFetchingNextPage) {
 *         loadMore();
 *       }
 *     };
 *
 *     window.addEventListener('scroll', handleScroll);
 *     return () => window.removeEventListener('scroll', handleScroll);
 *   });
 * </script>
 *
 * <div class="groups-grid">
 *   {#each $data as group}
 *     <GroupItem {group} />
 *   {/each}
 * </div>
 * ```
 */
export const useGroupsInfinite = (collectionId: string) => {
    const readGroupsOptions = getAllGroupsInfiniteOptions({
        query: { limit: 10 },
        body: {
            filter: {
                sample_filter: {
                    collection_id: collectionId
                }
            }
        }
    });

    const query = createInfiniteQuery({
        ...readGroupsOptions,
        getNextPageParam: (lastPage) => lastPage.nextCursor || undefined
    });

    const client = useQueryClient();
    const refresh = () => {
        client.invalidateQueries({ queryKey: readGroupsOptions.queryKey });
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
