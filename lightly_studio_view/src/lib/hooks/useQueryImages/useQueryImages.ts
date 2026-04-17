import type { InfiniteData } from '@tanstack/svelte-query';
import { createInfiniteQuery, infiniteQueryOptions } from '@tanstack/svelte-query';
import { queryImages } from '$lib/api/lightly_studio_local';
import type { QueryImagesError, QueryImagesResponse } from '$lib/api/lightly_studio_local';
import type { ImagesInfiniteParams } from '$lib/hooks/useImagesInfinite/useImagesInfinite';
import { buildRequestBody } from '$lib/hooks/useImagesInfinite/useImagesInfinite';

type UseQueryImagesParams = ImagesInfiniteParams & {
    queryText: string;
};

type QueryImagesQueryKey = readonly [
    string,
    string,
    string,
    'normal' | 'classifier',
    object | undefined,
    {
        metadata_values?: ImagesInfiniteParams['metadata_values'];
        text_embedding?: ImagesInfiniteParams['text_embedding'];
    }
];

const createQueryImagesOptions = (params: UseQueryImagesParams) => {
    const queryKey: QueryImagesQueryKey = [
        'queryImages',
        params.collection_id,
        params.queryText,
        params.mode,
        params.mode === 'normal' ? params.filters : params.classifierSamples,
        {
            metadata_values: params.metadata_values,
            text_embedding: params.text_embedding
        }
    ];

    return infiniteQueryOptions<
        QueryImagesResponse,
        QueryImagesError,
        InfiniteData<QueryImagesResponse>,
        QueryImagesQueryKey,
        number
    >({
        queryKey,
        queryFn: async ({ pageParam = 0, signal }) => {
            const requestBody = buildRequestBody(params, pageParam);

            const { data } = await queryImages({
                path: { collection_id: params.collection_id },
                body: {
                    ...requestBody,
                    text: params.queryText
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
