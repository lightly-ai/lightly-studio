import { createInfiniteQuery, useQueryClient } from '@tanstack/svelte-query';
import { readSamplesInfiniteOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { get, writable } from 'svelte/store';
import type { SampleView } from '$lib/api/lightly_studio_local/types.gen';

// export const useCaptionsInfinite = (...props: Parameters<typeof readSamplesInfiniteOptions>) => {
//     const readSamplesOptions = readSamplesInfiniteOptions(...props);
//     const samplesQuery = createInfiniteQuery({
//         ...readSamplesOptions,
//         getNextPageParam: (lastPage) => lastPage.nextCursor || undefined
//     });
//     const client = useQueryClient();
//     const refresh = () => {
//         client.invalidateQueries({ queryKey: readSamplesOptions.queryKey });
//     };

//     const data = writable<SampleView[]>([]);

//     samplesQuery.subscribe((query) => {
//         if (query.isSuccess) {
//             query.data.pages.flatMap((page) => page.data);
//         }
//     });

//     const loadMore = () => {
//         if (get(samplesQuery).hasNextPage && !get(samplesQuery).isFetchingNextPage) {
//             get(samplesQuery).fetchNextPage();
//         }
//     };

//     return {
//         data,
//         loadMore,
//         query: samplesQuery,
//         refresh
//     };
// };

export const useCaptionsInfinite = ({ datasetId, limit = 50 }: CaptionsInfiniteParams) => {
    const samplesOptions = readSamplesInfiniteOptions({
        body: { filters: { dataset_id: datasetId, has_captions: true } },
        query: { limit }
    });

    const samplesQuery = createInfiniteQuery({
        ...samplesOptions,
        getNextPageParam: (lastPage) => lastPage.nextCursor ?? undefined
    });

    const data = writable<SampleView[]>([]);
    samplesQuery.subscribe((query) => {
        if (query.isSuccess) {
            data.set(query.data.pages.flatMap((page) => page.data));
        }
    });

    const client = useQueryClient();
    return {
        data,
        loadMore: () => {
            const q = get(samplesQuery);
            if (q.hasNextPage && !q.isFetchingNextPage) q.fetchNextPage();
        },
        query: samplesQuery,
        refresh: () => client.invalidateQueries({ queryKey: samplesOptions.queryKey })
    };
};