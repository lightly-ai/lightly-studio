import {
    type AnnotationCreateInput,
    type CreateAnnotationResponse
} from '$lib/api/lightly_studio_local';
import { createAnnotationMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation } from '@tanstack/svelte-query';
import { usePostHog } from '$lib/hooks';
import { useInvalidateAnnotationQueries } from '$lib/hooks/useInvalidateAnnotationQueries';
import { page } from '$app/state';

export const useCreateAnnotation = ({ getCollectionId }: { getCollectionId: () => string }) => {
    const mutation = createMutation(() => createAnnotationMutation());
    const { trackEvent } = usePostHog();
    const refetch = useInvalidateAnnotationQueries();

    // Pass `skipRefetch` to create many annotations and call `refetch` once at the end.
    const createAnnotation = async (
        inputs: AnnotationCreateInput,
        { skipRefetch = false }: { skipRefetch?: boolean } = {}
    ): Promise<CreateAnnotationResponse> => {
        const collectionId = getCollectionId();
        // No per-call callbacks: TanStack drops them when the observer unmounts.
        const data = await mutation.mutateAsync({
            path: {
                collection_id: collectionId
            },
            body: inputs
        });
        if (!skipRefetch) refetch(collectionId);
        trackEvent('annotation_created', {
            collection_id: collectionId,
            annotation_type: data.annotation_type,
            parent_sample_type: page.params.collection_type,
            label_name: data.annotation_label.annotation_label_name
        });
        return data;
    };

    return {
        createAnnotation,
        refetch: () => refetch(getCollectionId())
    };
};
