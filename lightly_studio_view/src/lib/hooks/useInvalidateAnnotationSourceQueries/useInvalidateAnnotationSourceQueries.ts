import { useQueryClient } from '@tanstack/svelte-query';
import { ANNOTATIONS_INFINITE_QUERY_KEY_ROOT } from '$lib/hooks/useAnnotationsInfinite/createAnnotationsInfiniteOptions';
import { useInvalidateAnnotationQueries } from '$lib/hooks/useInvalidateAnnotationQueries';

// Partial keys on the `_id` of the generated query keys, for every collection and sample.
/** The annotation source lists, with and without annotation counts. */
const ANNOTATION_SOURCE_LIST_QUERY_KEYS = [
    [{ _id: 'readAnnotationCollections' }],
    [{ _id: 'readAnnotationCollectionsWithCounts' }]
];

// Queries that show annotations with their source: class counts and the sample details.
const SOURCE_DEPENDENT_QUERY_KEYS = [
    [{ _id: 'readAnnotationLabelsWithCounts' }],
    [{ _id: 'readImage' }],
    [{ _id: 'getFrameById' }],
    [{ _id: 'getVideoById' }],
    [{ _id: 'getAnnotationWithPayload' }]
];

/**
 * Returns the function that refreshes what deleting an annotation source of a collection
 * changes: what `useInvalidateAnnotationQueries` refreshes, plus the source lists of every
 * collection, the annotations grid, the class counts and the sample details. Call it on success
 * only.
 */
export const useInvalidateAnnotationSourceQueries = () => {
    const client = useQueryClient();
    const invalidateAnnotationQueries = useInvalidateAnnotationQueries();

    return (collectionId: string) => {
        invalidateAnnotationQueries(collectionId);
        // The annotations grid shows one source, keyed by the source, not by `collectionId`.
        client.invalidateQueries({ queryKey: [ANNOTATIONS_INFINITE_QUERY_KEY_ROOT] });
        for (const queryKey of [
            ...ANNOTATION_SOURCE_LIST_QUERY_KEYS,
            ...SOURCE_DEPENDENT_QUERY_KEYS
        ]) {
            client.invalidateQueries({ queryKey });
        }
    };
};
