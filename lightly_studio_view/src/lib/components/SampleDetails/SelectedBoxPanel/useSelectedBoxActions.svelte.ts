import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import { useAnnotationCollections, useMoveAnnotationsToSource } from '$lib/hooks';
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

/** Class change, move and delete for the selected box, with the same undo as the side panel. */
export const useSelectedBoxActions = (getParams: () => Params) => {
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
    const { addReversibleAction, updateLastAnnotationLabel } = useGlobalStorage();
    const { setAnnotationId, setAnnotationLabel } = useAnnotationLabelContext();

    const changeClass = async (labelName: string) => {
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
            label_name: labelName
        });
        setAnnotationLabel(labelName);
        updateLastAnnotationLabel(collectionId, labelName);
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

    const remove = async () => {
        const { annotation, refetch } = getParams();
        if (!labels.data) return;
        addAnnotationDeleteToUndoStack({
            annotation,
            labels: labels.data,
            sources: sources.data ?? [],
            addReversibleAction,
            createAnnotation,
            refetch
        });
        try {
            await deleteAnnotation(annotation.sample_id, annotation.annotation_type);
            toast.success('Annotation deleted successfully');
            setAnnotationId(null);
            refetch();
        } catch {
            toast.error('Failed to delete annotation. Please try again.');
        }
    };

    return { labels, sources, isMoving, changeClass, moveTo, remove };
};
