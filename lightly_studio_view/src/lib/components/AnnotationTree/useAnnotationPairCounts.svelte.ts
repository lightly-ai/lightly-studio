import { createQuery, keepPreviousData } from '@tanstack/svelte-query';
import { isEmpty, isNil, omit, omitBy } from 'lodash-es';
import type { ImageFilter } from '$lib/api/lightly_studio_local';
import {
    countImageAnnotationsByPair,
    countUnannotatedImagesBySource
} from '$lib/api/lightly_studio_local/sdk.gen';
import { useImageAnnotationCountsQueryKey } from '$lib/hooks/useImageAnnotationCounts/useImageAnnotationCounts';

interface CountsParams {
    collectionId: string;
    /** The grid filter. The tree's own ticks are removed from it. */
    filter?: ImageFilter | null;
    enabled?: boolean;
}

type CountsRequest = { path: { collection_id: string }; body: { filter?: ImageFilter } };

/** The filter without the tree ticks, so unticked rows keep their counts. */
export const withoutTreeTicks = (filter?: ImageFilter | null): ImageFilter | undefined => {
    const annotationsFilter = filter?.sample_filter?.annotations_filter;
    if (!filter || !annotationsFilter) return filter ?? undefined;
    const rest = omit(annotationsFilter, ['annotation_pairs', 'unannotated_collection_ids']);
    // An annotations filter with no other field still drops images without annotations.
    const hasOtherFields = !isEmpty(omitBy(omit(rest, 'filter_type'), isNil));
    return {
        ...filter,
        sample_filter: {
            ...omit(filter.sample_filter, 'annotations_filter'),
            ...(hasOtherFields ? { annotations_filter: rest } : {})
        }
    };
};

// The key extends the image annotation counts key, so invalidations after annotation edits
// reach these counts too.
const useTreeCounts = <T>(
    name: string,
    fetchCounts: (request: CountsRequest, signal: AbortSignal) => Promise<T>,
    getParams: () => CountsParams
) =>
    createQuery(() => {
        const { collectionId, filter, enabled = true } = getParams();
        const countsFilter = withoutTreeTicks(filter);
        const request = {
            path: { collection_id: collectionId },
            body: countsFilter ? { filter: countsFilter } : {}
        };
        return {
            queryKey: [...useImageAnnotationCountsQueryKey, name, request],
            queryFn: ({ signal }: { signal: AbortSignal }) => fetchCounts(request, signal),
            placeholderData: keepPreviousData,
            // The grids wait for these counts when ticks are off, so fail fast.
            retry: 1,
            enabled: enabled && Boolean(collectionId)
        };
    });

/** Annotation counts per (annotation source, annotation class) pair. */
export const useAnnotationPairCounts = (getParams: () => CountsParams) =>
    useTreeCounts(
        'by_pair',
        async (request, signal) =>
            (await countImageAnnotationsByPair({ ...request, signal, throwOnError: true })).data,
        getParams
    );

/** Counts of images without annotations per annotation source. */
export const useUnannotatedImageCounts = (getParams: () => CountsParams) =>
    useTreeCounts(
        'unannotated_by_source',
        async (request, signal) =>
            (await countUnannotatedImagesBySource({ ...request, signal, throwOnError: true })).data,
        getParams
    );
