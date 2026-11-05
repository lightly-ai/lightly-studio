import { toast } from 'svelte-sonner';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { useAnnotationCollections } from '$lib/hooks/useAnnotationCollections/useAnnotationCollections';
import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
import { useCreateAnnotation } from '$lib/hooks/useCreateAnnotation/useCreateAnnotation';
import { useDeleteAnnotation } from '$lib/hooks/useDeleteAnnotation/useDeleteAnnotation';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { addAnnotationDeleteToUndoStack } from '$lib/services/addAnnotationDeleteToUndoStack';

/**
 * Returns the action that deletes an annotation and, once the delete succeeded, adds the undo
 * that re-creates it in its class and source. A second call while one runs is ignored, so a
 * double click deletes once and adds one undo entry. Call it during component init.
 */
export const useDeleteAnnotationWithUndo = (getCollectionId: () => string) => {
    const labels = useAnnotationLabels(() => ({ collectionId: getCollectionId() }));
    const sources = useAnnotationCollections(() => ({ collectionId: getCollectionId() }));
    const { createAnnotation } = useCreateAnnotation({ getCollectionId });
    const { deleteAnnotation } = useDeleteAnnotation({ getCollectionId });
    const { addReversibleAction } = useGlobalStorage();

    let isDeleting = false;
    /** Resolves to whether the annotation was deleted. */
    const deleteWithUndo = async (
        annotation: AnnotationView,
        refetch: () => void
    ): Promise<boolean> => {
        if (!labels.data || isDeleting) return false;
        // Read before the request: undo re-creates the annotation as it was.
        const undoLabels = labels.data;
        const undoSources = sources.data ?? [];
        isDeleting = true;
        try {
            await deleteAnnotation(annotation.sample_id, annotation.annotation_type);
            addAnnotationDeleteToUndoStack({
                annotation,
                labels: undoLabels,
                sources: undoSources,
                addReversibleAction,
                createAnnotation,
                refetch
            });
            toast.success('Annotation deleted successfully');
            refetch();
            return true;
        } catch {
            toast.error('Failed to delete annotation. Please try again.');
            return false;
        } finally {
            isDeleting = false;
        }
    };

    return { deleteWithUndo };
};
