import { useQueryClient } from '@tanstack/svelte-query';
import { toast } from 'svelte-sonner';
import { getTickDetailsSequenceQueryKey, useUpdateAnnotationsMutation } from '$lib/hooks';

interface Params {
    getCollectionId: () => string | undefined;
    getDatasetId: () => string;
    getSequenceId: () => string;
    onUpdated: () => Promise<unknown>;
}

interface UseUpdateCuboidClassReturn {
    handleLabelChange: (annotationId: string, className: string) => Promise<void>;
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

    async function handleLabelChange(annotationId: string, className: string): Promise<void> {
        try {
            await updateAnnotations([
                {
                    annotation_id: annotationId,
                    collection_id: getCollectionId() ?? '',
                    label_name: className
                }
            ]);
            void queryClient.invalidateQueries({
                queryKey: getTickDetailsSequenceQueryKey({
                    datasetId: getDatasetId(),
                    sequenceId: getSequenceId()
                })
            });
            await onUpdated();
        } catch {
            toast.error('Failed to update annotation class. Please try again.');
        }
    }

    return { handleLabelChange };
}
