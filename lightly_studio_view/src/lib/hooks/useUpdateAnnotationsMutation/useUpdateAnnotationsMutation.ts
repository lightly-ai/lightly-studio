import { type AnnotationUpdateInput } from '$lib/api/lightly_studio_local';
import { updateAnnotationsMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation, useQueryClient } from '@tanstack/svelte-query';
import { useImageAnnotationCountsQueryKey } from '$lib/hooks/useImageAnnotationCounts/useImageAnnotationCounts';
import { usePostHog } from '$lib/hooks';

export const useUpdateAnnotationsMutation = ({
    getCollectionId
}: {
    getCollectionId: () => string;
}) => {
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
            const collectionId = getCollectionId();
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
                        if (inputs.length === 1) {
                            trackEvent('annotation_label_updated', {
                                collection_id: collectionId,
                                annotation_id: inputs[0].annotation_id,
                                label_name: labelInputs[0]?.label_name
                            });
                        } else if (inputs.length > 1) {
                            trackEvent('annotations_bulk_labeled', {
                                collection_id: collectionId,
                                annotation_ids: inputs.map((input) => input.annotation_id),
                                annotation_count: inputs.length
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
