import type { AnnotationCreateInput, AnnotationView } from '$lib/api/lightly_studio_local';
import {
    useAnnotationCollections,
    useAnnotationLabels,
    useCreateAnnotation,
    useDeleteAnnotation,
    useGlobalStorage
} from '$lib/hooks';
import { addAnnotationMoveToUndoStack } from '$lib/services/addAnnotationMoveToUndoStack';
import { toast } from 'svelte-sonner';

/**
 * Moves an annotation to another annotation source by copying it there and deleting the
 * original, with undo. The copy keeps the class, type, parent sample and geometry, but not the
 * confidence. When the delete fails, the copy stays and the original is reported as still there.
 * A move that starts while another runs does nothing.
 */
export const useMoveAnnotationByCopy = (getCollectionId: () => string) => {
    const labels = useAnnotationLabels(() => ({ collectionId: getCollectionId() }));
    const sources = useAnnotationCollections(() => ({ collectionId: getCollectionId() }));
    const { createAnnotation } = useCreateAnnotation({ getCollectionId });
    const { deleteAnnotation } = useDeleteAnnotation({ getCollectionId });
    const { addReversibleAction } = useGlobalStorage();
    let isMoving = $state(false);

    /** The ID of the copy, or null when nothing was copied. */
    const moveByCopy = async (
        annotation: AnnotationView,
        sourceName: string,
        refetch: () => void
    ): Promise<string | null> => {
        if (isMoving) return null;
        const labelName = annotation.annotation_label.annotation_label_name;
        const label = labels.data?.find((label) => label.annotation_label_name === labelName);
        // Undo re-creates the original in its source, so the move waits for the source names.
        const originalSource = sources.data?.find(
            (source) => source.collection_id === annotation.annotation_collection_id
        );
        if (!label?.annotation_label_id || !originalSource) {
            toast.error('Annotation classes and sources are still loading. Please try again.');
            return null;
        }
        const copyInput: AnnotationCreateInput = {
            annotation_label_id: label.annotation_label_id,
            annotation_type: annotation.annotation_type,
            annotation_collection_name: sourceName,
            parent_sample_id: annotation.parent_sample_id,
            ...annotation.object_detection_details,
            ...annotation.segmentation_details
        };
        isMoving = true;
        try {
            return await copyThenDelete({
                annotation,
                copyInput,
                originalInput: { ...copyInput, annotation_collection_name: originalSource.name },
                refetch
            });
        } finally {
            isMoving = false;
        }
    };

    const copyThenDelete = async ({
        annotation,
        copyInput,
        originalInput,
        refetch
    }: {
        annotation: AnnotationView;
        copyInput: AnnotationCreateInput;
        originalInput: AnnotationCreateInput;
        refetch: () => void;
    }): Promise<string | null> => {
        let copy: { sample_id: string; annotation_type: string };
        try {
            copy = await createAnnotation(copyInput);
        } catch {
            toast.error('Could not move the annotation. Please try again.');
            return null;
        }
        let isOriginalDeleted = true;
        try {
            await deleteAnnotation(annotation.sample_id, annotation.annotation_type);
        } catch {
            isOriginalDeleted = false;
            toast.error(
                `Copied to ${copyInput.annotation_collection_name}, but the original is still there.`
            );
        }
        addAnnotationMoveToUndoStack({
            copy,
            original: isOriginalDeleted ? originalInput : null,
            addReversibleAction,
            createAnnotation,
            deleteAnnotation,
            refetch
        });
        return copy.sample_id;
    };

    return {
        moveByCopy,
        get isMoving() {
            return isMoving;
        }
    };
};
