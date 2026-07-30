import { getAllFramesInfiniteOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';

import { createInfiniteQuery, useQueryClient } from '@tanstack/svelte-query';
import type { VideoFrameFilter } from '$lib/api/lightly_studio_local/types.gen';
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

    const loadMore = () => {
        if (query.hasNextPage && !query.isFetchingNextPage) {
            query.fetchNextPage();
        }
    };

    return {
        query,
        loadMore,
        refresh
    };
};
