import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import { useAnnotationCollections, useMoveAnnotationsToSource, useStickyClass } from '$lib/hooks';
import { useAnnotation } from '$lib/hooks/useAnnotation/useAnnotation';
import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
import { useCreateAnnotation } from '$lib/hooks/useCreateAnnotation/useCreateAnnotation';
import { useDeleteAnnotation } from '$lib/hooks/useDeleteAnnotation/useDeleteAnnotation';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { useUpdateAnnotationsMutation } from '$lib/hooks/useUpdateAnnotationsMutation/useUpdateAnnotationsMutation';
import { addAnnotationDeleteToUndoStack } from '$lib/services/addAnnotationDeleteToUndoStack';
import { addAnnotationLabelChangeToUndoStack } from '$lib/services/addAnnotationLabelChangeToUndoStack';
import { toast } from 'svelte-sonner';

interface Params {
    /** The collection that owns the annotation sources. */
    collectionId: string;
    annotation: AnnotationView;
    refetch: () => void;
}

/**
 * Class change, move and delete for the selected annotation, with the same undo as the side
 * panel. Call during component init: it reads the annotation label context.
 */
export const useAnnotationCardActions = (getParams: () => Params) => {
    const getCollectionId = () => getParams().collectionId;
    const labels = useAnnotationLabels(() => ({ collectionId: getCollectionId() }));
    const sources = useAnnotationCollections(() => ({ collectionId: getCollectionId() }));
    const { updateAnnotation } = useAnnotation(() => ({
        collectionId: getCollectionId(),
        annotationId: getParams().annotation.sample_id,
        onUpdate: getParams().refetch
    }));
    const { updateAnnotations } = useUpdateAnnotationsMutation({ getCollectionId });
    const { createAnnotation } = useCreateAnnotation({ getCollectionId });
    const { deleteAnnotation } = useDeleteAnnotation({ getCollectionId });
    const { moveToSource, isPending: isMoving } = useMoveAnnotationsToSource();
    const { addReversibleAction } = useGlobalStorage();
    const { setAnnotationId } = useAnnotationLabelContext();
    const { pickClass } = useStickyClass();

    const changeClass = async (className: string) => {
        const { annotation, collectionId, refetch } = getParams();
        addAnnotationLabelChangeToUndoStack({
            annotations: [annotation],
            collectionId,
            addReversibleAction,
            updateAnnotations,
            refresh: refetch
        });
        await updateAnnotation({
            annotation_id: annotation.sample_id,
            collection_id: collectionId,
            label_name: className
        });
        pickClass(collectionId, className);
    };

    const moveTo = async (sourceName: string) => {
        const { annotation, collectionId, refetch } = getParams();
        const moved = await moveToSource({
            collectionId,
            annotationIds: [annotation.sample_id],
            sourceName
        });
        if (moved) refetch();
        return moved;
    };

    // A second Delete while the first request runs would delete twice and add two undo entries.
    let isDeleting = false;
    const remove = async () => {
        const { annotation, refetch } = getParams();
        if (!labels.data || isDeleting) return;
        // Read before the request: undo recreates the annotation as it was.
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
            setAnnotationId(null);
            refetch();
        } catch {
            toast.error('Failed to delete annotation. Please try again.');
        } finally {
            isDeleting = false;
        }
    };

    const close = () => setAnnotationId(null);

    return { labels, sources, isMoving, changeClass, moveTo, remove, close };
};
