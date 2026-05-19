import { getAllVideosInfiniteOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';

import { createInfiniteQuery, useQueryClient } from '@tanstack/svelte-query';
import { writable } from 'svelte/store';
import type { VideoFilter, VideoView } from '$lib/api/lightly_studio_local/types.gen';
import { GRID_PAGE_SIZE } from '$lib/constants';

export const useVideos = (
    getParams: () => {
        collection_id: string;
        filter: VideoFilter;
        text_embedding?: Array<number>;
    }
) => {
    const query = createInfiniteQuery(() => {
        const { collection_id, filter, text_embedding } = getParams();
        return {
            ...getAllVideosInfiniteOptions({
                path: { collection_id },
                query: { limit: GRID_PAGE_SIZE },
                body: { filter, text_embedding }
            }),
            getNextPageParam: (lastPage) => lastPage.nextCursor || undefined
        };
    });
    const client = useQueryClient();
    const refresh = () => {
        const { collection_id, filter, text_embedding } = getParams();
        const options = getAllVideosInfiniteOptions({
            path: { collection_id },
            query: { limit: GRID_PAGE_SIZE },
            body: { filter, text_embedding }
        });
        client.invalidateQueries({ queryKey: options.queryKey });
    };

    const data = writable<VideoView[]>([]);
    const totalCount = writable(0);

    $effect(() => {
        if (query.isSuccess) {
            const videos = query.data.pages.flatMap((page) => page.data);
            data.set(videos);
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
        query: query,
        refresh,
        totalCount
    };
};
