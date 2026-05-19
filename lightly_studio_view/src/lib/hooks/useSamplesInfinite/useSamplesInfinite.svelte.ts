import { createInfiniteQuery, useQueryClient } from '@tanstack/svelte-query';
import { readSamplesInfiniteOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { writable } from 'svelte/store';
import type { SampleView } from '$lib/api/lightly_studio_local/types.gen';

export const useSamplesInfinite = (
    getProps: () => Parameters<typeof readSamplesInfiniteOptions>[0]
) => {
    const samplesQuery = createInfiniteQuery(() => ({
        ...readSamplesInfiniteOptions(getProps()),
        getNextPageParam: (lastPage) => lastPage.nextCursor || undefined
    }));
    const client = useQueryClient();
    const refresh = async () => {
        const queryKey = readSamplesInfiniteOptions(getProps()).queryKey;
        await client.refetchQueries({ queryKey });
    };

    const data = writable<SampleView[]>([]);

    $effect(() => {
        // Read dataUpdatedAt to track it as a reactive dependency for this $effect.
        void samplesQuery.dataUpdatedAt;
        if (samplesQuery.isSuccess) {
            const allSamples = samplesQuery.data.pages.flatMap((page) => page.data);
            data.set(allSamples);
        }
    });

    const loadMore = () => {
        if (samplesQuery.hasNextPage && !samplesQuery.isFetchingNextPage) {
            samplesQuery.fetchNextPage();
        }
    };

    return {
        data,
        loadMore,
        query: samplesQuery,
        refresh
    };
};
