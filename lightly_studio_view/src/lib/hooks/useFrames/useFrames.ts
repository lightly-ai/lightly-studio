import { getAllFramesInfiniteOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';

import { createInfiniteQuery, useQueryClient } from '@tanstack/svelte-query';
import { get, writable } from 'svelte/store';
import type { VideoFrameFilter, VideoFrameView } from '$lib/api/lightly_studio_local/types.gen';

export const useFrames = (video_frame_dataset_id: string, filter: VideoFrameFilter) => {
    const readCaptionsOptions = getAllFramesInfiniteOptions({
        path: { video_frame_dataset_id },
        query: { limit: 30 },
        body: {
            filter
        }
    });
    const query = createInfiniteQuery({
        ...readCaptionsOptions,
        getNextPageParam: (lastPage) => lastPage.nextCursor || undefined
    });
    const client = useQueryClient();
    const refresh = () => {
        client.invalidateQueries({ queryKey: readCaptionsOptions.queryKey });
    };

    const data = writable<VideoFrameView[]>([]);

    query.subscribe((query) => {
        if (query.isSuccess) {
            const frames = query.data.pages.flatMap((page) => page.data);
            data.set(frames);
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
