import {
    type AnnotationCreateInput,
    type CreateAnnotationResponse
} from '$lib/api/lightly_studio_local';
import {
    createAnnotationMutation,
    readAnnotationCollectionsQueryKey
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation, useQueryClient } from '@tanstack/svelte-query';
import { useImageAnnotationCountsQueryKey } from '$lib/hooks/useImageAnnotationCounts/useImageAnnotationCounts';
import { usePostHog } from '$lib/hooks';
import { useInvalidateAnnotationGridQueries } from '$lib/hooks/useInvalidateAnnotationGridQueries';
import { page } from '$app/state';

export const useCreateAnnotation = ({ collectionId }: { collectionId: string }) => {
    const mutation = createMutation(() => createAnnotationMutation());
    const client = useQueryClient();
    const { trackEvent } = usePostHog();
    const invalidateAnnotationGridQueries = useInvalidateAnnotationGridQueries({ collectionId });

    const refetch = () => {
        invalidateAnnotationGridQueries();
        client.invalidateQueries({
            queryKey: useImageAnnotationCountsQueryKey
        });
        // An annotation can be written to a brand-new source (collection) by name, so refresh
        // the source list to surface it in the pill and the side panel.
        client.invalidateQueries({
            queryKey: readAnnotationCollectionsQueryKey({ path: { collection_id: collectionId } })
        });
    };

    const createAnnotation = (inputs: AnnotationCreateInput) =>
        new Promise<CreateAnnotationResponse>((resolve, reject) => {
            mutation.mutate(
                {
                    path: {
                        collection_id: collectionId
                    },
                    body: inputs
                },
                {
                    onSuccess: (data) => {
                        refetch();
                        trackEvent('annotation_created', {
                            collection_id: collectionId,
                            annotation_type: data.annotation_type,
                            parent_sample_type: page.params.collection_type,
                            label_name: data.annotation_label.annotation_label_name
                        });
                        resolve(data);
                    },
                    onError: (error) => {
                        reject(error);
                    }
                }
            );
        });

    return {
        createAnnotation
    };
};
