import { createQuery } from '@tanstack/svelte-query';
import type { AnnotationCountMode, ImageFilter } from '$lib/api/lightly_studio_local';
import { countImageAnnotationsBySource } from '$lib/api/lightly_studio_local/sdk.gen';
import { useImageAnnotationCountsQueryKey } from '$lib/hooks/useImageAnnotationCounts/useImageAnnotationCounts';

/**
 * Image annotation counts per (annotation source, annotation class) pair.
 *
 * The key extends `useImageAnnotationCountsQueryKey`, so the invalidations after annotation
 * edits reach these counts too.
 */
export const useSourceLabelCounts = (
    getParams: () => { collectionId: string; filter?: ImageFilter; countMode: AnnotationCountMode }
) =>
    createQuery(() => {
        const { collectionId, filter, countMode } = getParams();
        const request = {
            path: { collection_id: collectionId },
            body: { ...(filter ? { filter } : {}), count_mode: countMode }
        };
        return {
            queryKey: [...useImageAnnotationCountsQueryKey, 'by_source', request],
            queryFn: async ({ signal }: { signal: AbortSignal }) => {
                const { data } = await countImageAnnotationsBySource({
                    ...request,
                    signal,
                    throwOnError: true
                });
                return data;
            },
            placeholderData: <T>(previousData: T) => previousData,
            enabled: Boolean(collectionId)
        };
    });
