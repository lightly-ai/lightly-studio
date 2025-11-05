import { createInfiniteQuery, useQueryClient } from '@tanstack/svelte-query';
import { readSamplesWithCaptionsInfiniteOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { get, writable } from 'svelte/store';
import type { SampleView } from '$lib/api/lightly_studio_local';

export const useCaptionsInfinite = (...props: Parameters<typeof readSamplesWithCaptionsInfiniteOptions>) => {
    const readCaptionsOptions = readSamplesWithCaptionsInfiniteOptions(...props);
    const captionsQuery = createInfiniteQuery({
        ...readCaptionsOptions,
        getNextPageParam: (lastPage) => lastPage.nextCursor || undefined
    });
    const client = useQueryClient();
    const refresh = () => {
        client.invalidateQueries({ queryKey: readCaptionsOptions.queryKey });
    };

    const data = writable<SampleView[]>([]);

    captionsQuery.subscribe((query) => {
        if (query.isSuccess) {
            data.set(query.data.pages.flatMap((page) => page.data));
        }
    });

    const loadMore = () => {
        if (get(captionsQuery).hasNextPage && !get(captionsQuery).isFetchingNextPage) {
            get(captionsQuery).fetchNextPage();
        }
    };

    return {
        data,
        loadMore,
        query: captionsQuery,
        refresh
    };
};
