import { getAllVideosInfiniteOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';

import { createInfiniteQuery, useQueryClient } from '@tanstack/svelte-query';
import { get, writable } from 'svelte/store';
import type { VideoView } from '$lib/api/lightly_studio_local/types.gen';

export const useVideos = (...props: Parameters<typeof getAllVideosInfiniteOptions>) => {
    const readCaptionsOptions = getAllVideosInfiniteOptions(...props);
    const query = createInfiniteQuery({
        ...readCaptionsOptions,
        getNextPageParam: (lastPage) => lastPage.nextCursor || undefined
    });
    const client = useQueryClient();
    const refresh = () => {
        client.invalidateQueries({ queryKey: readCaptionsOptions.queryKey });
    };

    const data = writable<VideoView[]>([]);

    query.subscribe((query) => {
        if (query.isSuccess) {
            const videos = query.data.pages.flatMap((page) => page.data);
            
            data.set(videos);
        }
    });

    const loadMore = () => {
        if (get(query).hasNextPage && !get(query).isFetchingNextPage) {
            get(query).fetchNextPage();
        }
    };

    return {
        data,
        loadMore,
        query: query,
        refresh
    };
};
