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
 * that re-creates it in its class and source. A second call for an annotation whose delete runs
 * is ignored, so a double click deletes once and adds one undo entry. Nothing is deleted while
 * the classes or sources load, as the undo needs both. Call it during component init.
 */
export const useDeleteAnnotationWithUndo = (getCollectionId: () => string) => {
    const labels = useAnnotationLabels(() => ({ collectionId: getCollectionId() }));
    const sources = useAnnotationCollections(() => ({ collectionId: getCollectionId() }));
    const { createAnnotation } = useCreateAnnotation({ getCollectionId });
    const { deleteAnnotation } = useDeleteAnnotation({ getCollectionId });
    const { addReversibleAction } = useGlobalStorage();

    // The annotations whose delete runs.
    const deletingIds = new Set<string>();
    /** Resolves to whether the annotation was deleted. */
    const deleteWithUndo = async (
        annotation: AnnotationView,
        refetch: () => void
    ): Promise<boolean> => {
        if (!labels.data || !sources.data || deletingIds.has(annotation.sample_id)) return false;
        // Read before the request: undo re-creates the annotation as it was.
        const undoLabels = labels.data;
        const undoSources = sources.data;
        deletingIds.add(annotation.sample_id);
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
            deletingIds.delete(annotation.sample_id);
        }
    };

    return { deleteWithUndo };
};
