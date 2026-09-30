import { deleteAnnotationsMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation } from '@tanstack/svelte-query';
import { usePostHog } from '$lib/hooks/usePostHog';
import { useInvalidateAnnotationDeleteQueries } from '$lib/hooks/useInvalidateAnnotationDeleteQueries/useInvalidateAnnotationDeleteQueries';

interface UseDeleteAnnotationsParams {
    /** The annotation collection that the annotations belong to. */
    getCollectionId: () => string;
}

export const useDeleteAnnotations = ({ getCollectionId }: UseDeleteAnnotationsParams) => {
    const mutation = createMutation(() => deleteAnnotationsMutation());
    const { trackEvent } = usePostHog();
    const invalidateAnnotationDeleteQueries = useInvalidateAnnotationDeleteQueries();

    // TODO(Nauryzbay, 09/2026): Add a delete by filter, so that a large select-all selection
    // does not send every annotation ID in the request body.
    const deleteAnnotations = async (annotationIds: string[]): Promise<number> => {
        const collectionId = getCollectionId();
        const { deleted_count } = await mutation.mutateAsync({
            path: { collection_id: collectionId },
            body: { annotation_ids: annotationIds }
        });
        invalidateAnnotationDeleteQueries(collectionId);
        trackEvent('annotations_deleted', { collection_id: collectionId, count: deleted_count });
        return deleted_count;
    };

    return { deleteAnnotations };
};
