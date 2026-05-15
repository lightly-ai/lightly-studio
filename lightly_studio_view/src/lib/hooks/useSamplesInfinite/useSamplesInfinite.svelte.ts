import { createInfiniteQuery, useQueryClient } from '@tanstack/svelte-query';
import { readSamplesInfiniteOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { writable } from 'svelte/store';
import type { SampleView } from '$lib/api/lightly_studio_local/types.gen';

export const useSamplesInfinite = (...props: Parameters<typeof readSamplesInfiniteOptions>) => {
    const readSamplesOptions = readSamplesInfiniteOptions(...props);
    const samplesQuery = createInfiniteQuery(() => ({
        ...readSamplesOptions,
        getNextPageParam: (lastPage) => lastPage.nextCursor || undefined
    }));
    const client = useQueryClient();
    const queryKey = readSamplesOptions.queryKey;
    const refresh = async () => {
        await client.refetchQueries({ queryKey });
    };

    const data = writable<SampleView[]>([]);

    $effect(() => {
        samplesQuery.dataUpdatedAt;
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
