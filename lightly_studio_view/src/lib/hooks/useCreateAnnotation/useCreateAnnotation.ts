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

export const useCreateAnnotation = ({ collectionId }: { collectionId: string }) => {
    const mutation = createMutation(() => createAnnotationMutation());
    const client = useQueryClient();

    const refetch = () => {
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
