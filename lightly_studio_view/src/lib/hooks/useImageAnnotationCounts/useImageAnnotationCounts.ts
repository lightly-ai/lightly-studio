import { createQuery } from '@tanstack/svelte-query';
import type { AnnotationType, ImageFilter } from '$lib/api/lightly_studio_local';
import {
    countImageAnnotationsByCollectionOptions,
    countImageAnnotationsByCollectionQueryKey
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { countImageAnnotationsByCollection } from '$lib/api/lightly_studio_local/sdk.gen';

export const useImageAnnotationCountsQueryKey = countImageAnnotationsByCollectionQueryKey({
    path: { collection_id: '__static_value__' }
});

export const useImageAnnotationCounts = ({
    collectionId,
    filter,
    annotationType
}: {
    collectionId: string;
    filter?: ImageFilter;
    /** Restrict counts to a single annotation type (e.g. classification). */
    annotationType?: AnnotationType;
}) => {
    const requestOptions = {
        path: { collection_id: collectionId },
        ...(filter || annotationType
            ? {
                  body: {
                      ...(filter ? { filter } : {}),
                      ...(annotationType ? { annotation_type: annotationType } : {})
                  }
              }
            : {})
    } as const;

    const options = countImageAnnotationsByCollectionOptions(requestOptions);
    // Keep the collection id static so annotation mutations invalidate every
    // variant, but discriminate by annotation type so the per-type queries
    // don't collide in the cache.
    const queryKey = annotationType
        ? countImageAnnotationsByCollectionQueryKey({
              path: { collection_id: '__static_value__' },
              body: { annotation_type: annotationType }
          })
        : useImageAnnotationCountsQueryKey;

    return createQuery(() => ({
        ...options,
        queryKey,
        queryFn: async ({ signal }) => {
            const { data } = await countImageAnnotationsByCollection({
                ...requestOptions,
                signal,
                throwOnError: true
            });
            return data;
        }
    }));
};
