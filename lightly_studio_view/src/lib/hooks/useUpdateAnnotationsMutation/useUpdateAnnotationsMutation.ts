import { type AnnotationUpdateInput } from '$lib/api/lightly_studio_local';
import { updateAnnotationsMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation, useQueryClient } from '@tanstack/svelte-query';
import { useImageAnnotationCountsQueryKey } from '$lib/hooks/useImageAnnotationCounts/useImageAnnotationCounts';
import { usePostHog } from '$lib/hooks/usePostHog';

export const useUpdateAnnotationsMutation = ({ collectionId }: { collectionId: string }) => {
    const mutation = createMutation(() => updateAnnotationsMutation());

    const client = useQueryClient();
    const { trackEvent } = usePostHog();

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
                        const labelInputs = inputs.filter((input) => input.label_name != null);
                        if (labelInputs.length === 1) {
                            trackEvent('annotation_label_updated', {
                                collection_id: collectionId,
                                label_name: labelInputs[0].label_name
                            });
                        } else if (labelInputs.length > 1) {
                            trackEvent('annotations_bulk_labeled', {
                                collection_id: collectionId,
                                annotation_count: labelInputs.length,
                                label_names: labelInputs.map((input) => input.label_name)
                            });
                        }
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
