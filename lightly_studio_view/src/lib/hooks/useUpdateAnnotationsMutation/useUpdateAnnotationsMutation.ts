import { type AnnotationUpdateInput } from '$lib/api/lightly_studio_local';
import { updateAnnotationsMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation, useQueryClient } from '@tanstack/svelte-query';
import { useImageAnnotationCountsQueryKey } from '$lib/hooks/useImageAnnotationCounts/useImageAnnotationCounts';

export const useUpdateAnnotationsMutation = ({ collectionId }: { collectionId: string }) => {
    const mutation = createMutation(() => updateAnnotationsMutation());

    const client = useQueryClient();

    const refetch = () => {
        client.invalidateQueries({
            queryKey: useImageAnnotationCountsQueryKey
        });
    };

    const updateAnnotations = (inputs: AnnotationUpdateInput[]) =>
        new Promise<void>((resolve, reject) => {
            mutation.mutate(
                {
                    path: {
                        collection_id: collectionId
                    },
                    body: inputs
                },
                {
                    onSuccess: () => {
                        refetch();
                        resolve();
                    },
                    onError: (error) => {
                        reject(error);
                    }
                }
            );
        });

    return {
        updateAnnotations
    };
};
