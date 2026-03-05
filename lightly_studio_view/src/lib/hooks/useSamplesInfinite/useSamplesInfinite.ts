import { createInfiniteQuery, useQueryClient } from '@tanstack/svelte-query';
import { readSamplesInfiniteOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { derived, get, writable } from 'svelte/store';
import type { SampleView } from '$lib/api/lightly_studio_local/types.gen';
import { toReadable, type StoreOrVal } from '$lib/utils/reactiveParams';

type UseSamplesInfiniteParams = Parameters<typeof readSamplesInfiniteOptions>[0];

export const useSamplesInfinite = (params: StoreOrVal<UseSamplesInfiniteParams>) => {
    const paramsStore = toReadable(params);
    const optionsStore = derived(paramsStore, (currentParams) => {
        const readSamplesOpts = readSamplesInfiniteOptions(currentParams);
        return {
            ...readSamplesOpts,
            getNextPageParam: (lastPage: { nextCursor?: number | null }) =>
                lastPage.nextCursor ?? undefined
        };
    });

    const samplesQuery = createInfiniteQuery(optionsStore);
    const client = useQueryClient();
    const refresh = () => {
        client.invalidateQueries({
            queryKey: get(optionsStore).queryKey
        });
    };

    const data = writable<SampleView[]>([]);

    samplesQuery.subscribe((query) => {
        if (query.isSuccess) {
            const allCaptions = query.data.pages.flatMap((page) => page.data);
            data.set(allCaptions);
        }
    });

    const loadMore = () => {
        if (get(samplesQuery).hasNextPage && !get(samplesQuery).isFetchingNextPage) {
            get(samplesQuery).fetchNextPage();
        }
    };

    return {
        data,
        loadMore,
        query: samplesQuery,
        refresh
    };
};
