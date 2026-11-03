import { useQueryClient } from '@tanstack/svelte-query';
import { toast } from 'svelte-sonner';
import { getTickDetailsSequenceQueryKey, useUpdateAnnotationsMutation } from '$lib/hooks';
import { readAnnotationLabelsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';

interface Params {
    getCollectionId: () => string | undefined;
    getDatasetId: () => string;
    getSequenceId: () => string;
    onUpdated: () => Promise<unknown>;
}

interface UseUpdateCuboidClassReturn {
    handleLabelChange: (
        annotationId: string,
        className: string,
        annotationSourceId: string
    ) => Promise<void>;
}

/** Saves an annotation class and refreshes all cached ticks for its object track. */
export function useUpdateCuboidClass({
    getCollectionId,
    getDatasetId,
    getSequenceId,
    onUpdated
}: Params): UseUpdateCuboidClassReturn {
    const { updateAnnotations } = useUpdateAnnotationsMutation({
        getCollectionId: () => getCollectionId() ?? ''
    });
    const queryClient = useQueryClient();

    async function handleLabelChange(
        annotationId: string,
        className: string,
        annotationSourceId: string
    ): Promise<void> {
        try {
            await updateAnnotations([
                {
                    annotation_id: annotationId,
                    collection_id: getCollectionId() ?? '',
                    label_name: className
                }
            ]);
        } catch (error) {
            toast.error('Failed to update annotation class. Please try again.');
            throw error;
        }
        void queryClient.invalidateQueries({
            queryKey: getTickDetailsSequenceQueryKey({
                datasetId: getDatasetId(),
                sequenceId: getSequenceId()
            })
        });
        void queryClient.invalidateQueries({
            queryKey: readAnnotationLabelsOptions({
                path: { collection_id: annotationSourceId }
            }).queryKey
        });
        try {
            await onUpdated();
        } catch {
            toast.error(
                'Annotation class updated, but the workspace could not refresh. Please try again.'
            );
        }
    }

    return { handleLabelChange };
}
