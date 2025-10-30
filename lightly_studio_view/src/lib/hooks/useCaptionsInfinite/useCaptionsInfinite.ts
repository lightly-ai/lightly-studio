import { createInfiniteQuery, useQueryClient } from '@tanstack/svelte-query';
import { readCaptionsInfiniteOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { get, writable } from 'svelte/store';
import type { SampleCaptionDetailsView } from '$lib/api/lightly_studio_local/types.gen';

export const useCaptionsInfinite = (...props: Parameters<typeof readCaptionsInfiniteOptions>) => {
    const readCaptionsOptions = readCaptionsInfiniteOptions(...props);
    const captionsQuery = createInfiniteQuery({
        ...readCaptionsOptions,
        getNextPageParam: (lastPage) => lastPage.nextCursor || undefined
    });
    const client = useQueryClient();
    const refresh = () => {
        client.invalidateQueries({ queryKey: readCaptionsOptions.queryKey });
    };

    const data = writable<SampleCaptionDetailsView[]>([]);

    captionsQuery.subscribe((query) => {
        if (query.isSuccess) {
            data.set(query.data.pages.flatMap((e) => e.data));
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
