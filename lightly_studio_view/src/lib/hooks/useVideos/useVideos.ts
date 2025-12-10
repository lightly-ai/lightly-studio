import { getAllVideosInfiniteOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';

import { createInfiniteQuery, useQueryClient } from '@tanstack/svelte-query';
import { get, writable } from 'svelte/store';
import type {
    VideoFilter,
    VideoView,
    TextEmbedding
} from '$lib/api/lightly_studio_local/types.gen';

export const useVideos = (
    dataset_id: string,
    filter: VideoFilter,
    text_embedding?: TextEmbedding
) => {
    const body: { filter: VideoFilter; text_embedding?: TextEmbedding } = {
        filter
    };

    if (text_embedding) {
        body.text_embedding = text_embedding;
    }

    const readVideosOptions = getAllVideosInfiniteOptions({
        path: { dataset_id },
        query: { limit: 30 },
        body
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
