import { createQuery } from '@tanstack/svelte-query';
import { countVideoFrameAnnotationsByVideoCollectionOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { AnnotationType, VideoFilter } from '$lib/api/lightly_studio_local';

interface VideoAnnotationCountsParams {
    collectionId: string;
    filter?: VideoFilter | null;
    /** Restrict counts to a single annotation type (e.g. classification). */
    annotationType?: AnnotationType;
}

export function buildVideoAnnotationCountsRequest({
    collectionId,
    filter,
    annotationType
}: VideoAnnotationCountsParams) {
    return {
        path: { collection_id: collectionId },
        body: {
            filter,
            ...(annotationType ? { annotation_type: annotationType } : {})
        }
    };
}

/**
 * Counts the videos of each annotation class. A video counts for a class when
 * the video or one of its frames has an annotation of that class.
 */
export const useVideoAnnotationCounts = (
    getParams: () => VideoAnnotationCountsParams & {
        /** Set to false to prevent the query from fetching. Default: true. */
        enabled?: boolean;
    }
) =>
    createQuery(() => {
        const { enabled = true, ...params } = getParams();
        return {
            ...countVideoFrameAnnotationsByVideoCollectionOptions(
                buildVideoAnnotationCountsRequest(params)
            ),
            enabled
        };
    });
