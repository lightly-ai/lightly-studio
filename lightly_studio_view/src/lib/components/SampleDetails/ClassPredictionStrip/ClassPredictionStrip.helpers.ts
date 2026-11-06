import type { Query } from '@tanstack/svelte-query';

/**
 * Matches the getAnnotation queries of one annotation, whatever collection they were
 * fetched for. The side panel row and the box on the image read the class from them.
 */
export const isAnnotationQueryOf =
    (annotationId: string) =>
    (query: Pick<Query, 'queryKey'>): boolean => {
        const key = query.queryKey[0] as
            | { _id?: string; path?: { annotation_id?: string } }
            | undefined;
        return key?._id === 'getAnnotation' && key.path?.annotation_id === annotationId;
    };
