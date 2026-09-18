import { listMcapSequencesInfiniteOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { McapSequenceView } from '$lib/api/lightly_studio_local/types.gen';
import { GRID_PAGE_SIZE } from '$lib/constants';
import { createInfiniteQuery } from '@tanstack/svelte-query';
import { writable } from 'svelte/store';

export const useMcapSequences = (getCollectionId: () => string) => {
    const query = createInfiniteQuery(() => ({
        ...listMcapSequencesInfiniteOptions({
            path: { collection_id: getCollectionId() },
            query: { limit: GRID_PAGE_SIZE }
        }),
        getNextPageParam: (lastPage) => lastPage.nextCursor || undefined
    }));

    const data = writable<McapSequenceView[]>([]);

    $effect(() => {
        void query.dataUpdatedAt;
        if (query.isSuccess) {
            data.set(query.data.pages.flatMap((page) => page.data));
        }
    });

    const loadMore = () => {
        if (query.hasNextPage && !query.isFetchingNextPage) {
            void query.fetchNextPage();
        }
    };

    return { data, loadMore, query };
};
