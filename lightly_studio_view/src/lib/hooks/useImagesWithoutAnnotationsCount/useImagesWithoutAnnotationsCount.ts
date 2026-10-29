import { createQuery } from '@tanstack/svelte-query';
import type { ImageFilter } from '$lib/api/lightly_studio_local';
import { countImagesWithoutAnnotations } from '$lib/api/lightly_studio_local/sdk.gen';
import { useImageAnnotationCountsQueryKey } from '$lib/hooks/useImageAnnotationCounts/useImageAnnotationCounts';

/**
 * Counts the images without annotations in the selected annotation sources, for the
 * "No annotations" row of the annotation class filter.
 *
 * The key extends the annotation counts key, so annotation mutations refresh it too.
 */
export const useImagesWithoutAnnotationsCount = (
    getParams: () => { collectionId: string; filter?: ImageFilter; enabled?: boolean }
) =>
    createQuery(() => {
        const { collectionId, filter, enabled } = getParams();
        const request = { path: { collection_id: collectionId }, body: { filter } };
        return {
            queryKey: [...useImageAnnotationCountsQueryKey, 'withoutAnnotations', request],
            queryFn: async ({ signal }: { signal: AbortSignal }) => {
                const { data } = await countImagesWithoutAnnotations({
                    ...request,
                    signal,
                    throwOnError: true
                });
                return data;
            },
            placeholderData: <T>(previousData: T | undefined) => previousData,
            enabled: enabled ?? true
        };
    });
