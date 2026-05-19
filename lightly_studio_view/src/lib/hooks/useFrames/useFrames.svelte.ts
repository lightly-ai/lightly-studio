import { getAllFramesInfiniteOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';

import { createInfiniteQuery, useQueryClient } from '@tanstack/svelte-query';
import { writable } from 'svelte/store';
import type { VideoFrameFilter, VideoFrameView } from '$lib/api/lightly_studio_local/types.gen';
import { GRID_PAGE_SIZE } from '$lib/constants';

export const useFrames = (
    getParams: () => { video_frame_collection_id: string; filter: VideoFrameFilter }
) => {
    const query = createInfiniteQuery(() => {
        const { video_frame_collection_id, filter } = getParams();
        return {
            ...getAllFramesInfiniteOptions({
                path: { video_frame_collection_id },
                query: { limit: GRID_PAGE_SIZE },
                body: { filter }
            }),
            getNextPageParam: (lastPage) => lastPage.nextCursor || undefined
        };
    });
    const client = useQueryClient();
    const refresh = () => {
        const { video_frame_collection_id, filter } = getParams();
        const options = getAllFramesInfiniteOptions({
            path: { video_frame_collection_id },
            query: { limit: GRID_PAGE_SIZE },
            body: { filter }
        });
        client.invalidateQueries({ queryKey: options.queryKey });
    };

    const data = writable<VideoFrameView[]>([]);
    const totalCount = writable(0);
    $effect(() => {
        if (query.isSuccess) {
            const frames = query.data.pages.flatMap((page) => page.data);
            data.set(frames);
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
        totalCount,
        loadMore,
        query: query,
        refresh
    };
};
