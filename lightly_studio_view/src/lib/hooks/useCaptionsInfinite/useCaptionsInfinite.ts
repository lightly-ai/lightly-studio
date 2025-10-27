import { createInfiniteQuery, useQueryClient } from '@tanstack/svelte-query';
import { readCaptionsInfiniteOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { get, writable } from 'svelte/store';
import type { CaptionSampleView } from '$lib/api/lightly_studio_local/types.gen';

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

    const data = writable<CaptionSampleView[]>([]);

    captionsQuery.subscribe((query) => {
        if (query.isSuccess) {
            const allCaptions = query.data.pages.flatMap((page) => page.data);
            data.set(allCaptions);
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
