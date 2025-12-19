import { getAllVideosInfiniteOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';

import { createInfiniteQuery, useQueryClient } from '@tanstack/svelte-query';
import { get, writable } from 'svelte/store';
import type { VideoFilter, VideoView } from '$lib/api/lightly_studio_local/types.gen';

export const useVideos = (
    collection_id: string,
    filter: VideoFilter,
    text_embedding?: Array<number>
) => {
    const readVideosOptions = getAllVideosInfiniteOptions({
        path: { collection_id },
        query: { limit: 30 },
        body: {
            filter,
            text_embedding
        }
    });
    const query = createInfiniteQuery({
        ...readVideosOptions,
        getNextPageParam: (lastPage) => lastPage.nextCursor || undefined
    });
    const client = useQueryClient();
    const refresh = () => {
        client.invalidateQueries({ queryKey: readVideosOptions.queryKey });
    };

    const data = writable<VideoView[]>([]);
    const totalCount = writable(0);

    query.subscribe((query) => {
        if (query.isSuccess) {
            const videos = query.data.pages.flatMap((page) => page.data);
            data.set(videos);
            totalCount.set(query.data.pages[0].total_count);
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
        refresh,
        totalCount
    };
};
