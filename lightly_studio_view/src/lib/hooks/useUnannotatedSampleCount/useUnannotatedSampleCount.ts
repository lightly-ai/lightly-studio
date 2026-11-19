import { createQuery } from '@tanstack/svelte-query';
import {
    countUnannotatedImagesQueryKey,
    countUnannotatedVideosQueryKey
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import {
    countUnannotatedImages,
    countUnannotatedVideos
} from '$lib/api/lightly_studio_local/sdk.gen';
import type {
    ImageFilter,
    UnannotatedSampleCount,
    VideoFilter
} from '$lib/api/lightly_studio_local';
import { useImageAnnotationCountsQueryKey } from '$lib/hooks';

type CountRequest = { collectionId: string } & (
    | { sampleType: 'image'; filter?: ImageFilter }
    | { sampleType: 'video'; filter?: VideoFilter | null }
);

/** Counts the images or videos without annotations, in total and for the filter. */
export const useUnannotatedSampleCount = (
    getParams: () => CountRequest & {
        /** Set to false to prevent the query from fetching. Default: true. */
        enabled?: boolean;
    }
) =>
    createQuery(() => {
        const { enabled = true, ...request } = getParams();
        return {
            queryKey: buildQueryKey(request),
            queryFn: ({ signal }: { signal: AbortSignal }) => fetchCount(request, signal),
            // Keep the previous count while the request for a new filter runs.
            placeholderData: (previousData: UnannotatedSampleCount | undefined) => previousData,
            enabled
        };
    });

const buildQueryKey = (request: CountRequest): unknown[] => {
    const path = { collection_id: request.collectionId };
    if (request.sampleType === 'video') {
        return countUnannotatedVideosQueryKey({ path, body: { filter: request.filter } });
    }
    // Under the image count key, so that an annotation change refreshes this count too.
    return [
        ...useImageAnnotationCountsQueryKey,
        ...countUnannotatedImagesQueryKey({ path, body: { filter: request.filter } })
    ];
};

const fetchCount = async (
    request: CountRequest,
    signal: AbortSignal
): Promise<UnannotatedSampleCount> => {
    const path = { collection_id: request.collectionId };
    const { data } =
        request.sampleType === 'video'
            ? await countUnannotatedVideos({
                  path,
                  body: { filter: request.filter },
                  signal,
                  throwOnError: true
              })
            : await countUnannotatedImages({
                  path,
                  body: { filter: request.filter },
                  signal,
                  throwOnError: true
              });
    return data;
};
