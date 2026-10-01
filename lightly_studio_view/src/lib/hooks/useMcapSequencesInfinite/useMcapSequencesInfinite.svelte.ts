import { listMcapSequencesInfiniteOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createInfiniteQuery, useQueryClient } from '@tanstack/svelte-query';
import { type Writable, writable } from 'svelte/store';
import type { McapSequenceView } from '$lib/api/lightly_studio_local/types.gen';
import { GRID_PAGE_SIZE } from '$lib/constants';

interface UseMcapSequencesInfiniteReturn {
    data: Writable<McapSequenceView[]>;
    loadMore: () => void;
    query: ReturnType<typeof createInfiniteQuery>;
    refresh: () => void;
    totalCount: Writable<number>;
}

export const useMcapSequencesInfinite = (
    getCollectionId: () => string
): UseMcapSequencesInfiniteReturn => {
    const query = createInfiniteQuery(() => ({
        ...listMcapSequencesInfiniteOptions({
            path: { collection_id: getCollectionId() },
            query: { limit: GRID_PAGE_SIZE }
        }),
        getNextPageParam: (lastPage) => lastPage.nextCursor || undefined
    }));

    const client = useQueryClient();
    const refresh = () => {
        const options = listMcapSequencesInfiniteOptions({
            path: { collection_id: getCollectionId() },
            query: { limit: GRID_PAGE_SIZE }
        });
        client.invalidateQueries({ queryKey: options.queryKey });
    };

    const data = writable<McapSequenceView[]>([]);
    const totalCount = writable(0);

    $effect(() => {
        if (query.isSuccess) {
            const sequences = query.data.pages.flatMap((page) => page.data);
            data.set(sequences);
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
        query,
        refresh,
        totalCount
    };
};
