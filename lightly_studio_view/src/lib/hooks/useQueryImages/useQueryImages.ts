import type { InfiniteData } from '@tanstack/svelte-query';
import { createInfiniteQuery, infiniteQueryOptions } from '@tanstack/svelte-query';
import { queryImages } from '$lib/api/lightly_studio_local';
import type { QueryImagesError, QueryImagesResponse } from '$lib/api/lightly_studio_local';
import { GRID_PAGE_SIZE } from '$lib/constants';

interface UseQueryImagesParams {
    collectionId: string;
    queryText: string;
}

type QueryImagesQueryKey = readonly [string, string, string];

const createQueryImagesOptions = (params: UseQueryImagesParams) => {
    const queryKey: QueryImagesQueryKey = ['queryImages', params.collectionId, params.queryText];

    return infiniteQueryOptions<
        QueryImagesResponse,
        QueryImagesError,
        InfiniteData<QueryImagesResponse>,
        QueryImagesQueryKey,
        number
    >({
        queryKey,
        queryFn: async ({ pageParam = 0, signal }) => {
            const { data } = await queryImages({
                path: { collection_id: params.collectionId },
                body: {
                    text: params.queryText,
                    pagination: { offset: pageParam, limit: GRID_PAGE_SIZE }
                },
                signal,
                throwOnError: true
            });
            return data;
        },
        initialPageParam: 0,
        getNextPageParam: (lastPage) => lastPage.nextCursor ?? undefined,
        enabled: params.queryText.trim().length > 0
    });
};

export function useQueryImages(params: UseQueryImagesParams) {
    const options = createQueryImagesOptions(params);
    const samples = createInfiniteQuery(options);

    return { samples };
}
