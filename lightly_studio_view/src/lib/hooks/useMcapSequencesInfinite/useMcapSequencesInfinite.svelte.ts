import { listMcapSequencesInfiniteOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createInfiniteQuery, useQueryClient } from '@tanstack/svelte-query';
import { type Writable, writable } from 'svelte/store';
import type { McapSequenceFilter, McapSequenceView } from '$lib/api/lightly_studio_local/types.gen';
import { GRID_PAGE_SIZE } from '$lib/constants';

interface UseMcapSequencesInfiniteParams {
    collection_id: string;
    filter?: McapSequenceFilter | null;
}

interface UseMcapSequencesInfiniteReturn {
    data: Writable<McapSequenceView[]>;
    loadMore: () => void;
    query: ReturnType<typeof createInfiniteQuery>;
    refresh: () => void;
    totalCount: Writable<number>;
}

const buildOptions = ({ collection_id, filter }: UseMcapSequencesInfiniteParams) =>
    listMcapSequencesInfiniteOptions({
        path: { collection_id },
        query: { limit: GRID_PAGE_SIZE },
        body: { filter: filter ?? undefined }
    });

export const useMcapSequencesInfinite = (
    getParams: () => UseMcapSequencesInfiniteParams
): UseMcapSequencesInfiniteReturn => {
    const query = createInfiniteQuery(() => ({
        ...buildOptions(getParams()),
        getNextPageParam: (lastPage) => lastPage.nextCursor || undefined
    }));

    const client = useQueryClient();
    const refresh = () => {
        client.invalidateQueries({ queryKey: buildOptions(getParams()).queryKey });
    };

    const data = writable<McapSequenceView[]>([]);
    const totalCount = writable(0);

    $effect(() => {
        if (query.isSuccess) {
            const sequences = query.data.pages.flatMap((page) => page.data);
            data.set(sequences);
            totalCount.set(query.data.pages[0].total_count);
        } else if (query.isPending) {
            // A new query key without cached data must not show the previous filter's results.
            data.set([]);
            totalCount.set(0);
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
