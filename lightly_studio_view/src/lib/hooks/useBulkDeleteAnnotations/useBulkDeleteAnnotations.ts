import { bulkDeleteAnnotations } from '$lib/api/lightly_studio_local';
import { useInvalidateAnnotationGridQueries } from '$lib/hooks/useInvalidateAnnotationGridQueries';
import { useImageAnnotationCountsQueryKey } from '$lib/hooks/useImageAnnotationCounts/useImageAnnotationCounts';
import { useInvalidateEvaluationRunsQueries } from '$lib/hooks/useEvaluationRuns/useEvaluationRuns';
import { usePostHog } from '$lib/hooks';
import { useQueryClient } from '@tanstack/svelte-query';
import { toast } from 'svelte-sonner';

export const useBulkDeleteAnnotations = () => {
    const client = useQueryClient();
    const invalidateAnnotationGridQueries = useInvalidateAnnotationGridQueries();
    const invalidateEvaluationRunsQueries = useInvalidateEvaluationRunsQueries();
    const { trackEvent } = usePostHog();

    const deleteAnnotations = async ({
        collectionId,
        annotationIds
    }: {
        collectionId: string;
        annotationIds: string[];
    }) => {
        if (annotationIds.length === 0) return { deletedCount: 0, staleSelection: false };

        const response = await bulkDeleteAnnotations({
            path: { collection_id: collectionId },
            body: { annotation_ids: annotationIds }
        });
        if (response.error) {
            if (response.response.status === 400) {
                toast.error('Some selected annotations no longer belong to this source.');
                return { deletedCount: 0, staleSelection: true };
            }
            toast.error('Failed to delete annotations. Please try again.');
            throw response.error;
        }

        invalidateAnnotationGridQueries(collectionId);
        client.invalidateQueries({ queryKey: useImageAnnotationCountsQueryKey });
        invalidateEvaluationRunsQueries();
        trackEvent('annotations_bulk_deleted', {
            collection_id: collectionId,
            annotation_count: annotationIds.length
        });
        return { deletedCount: response.data.deleted_count, staleSelection: false };
    };

    return { deleteAnnotations };
};
