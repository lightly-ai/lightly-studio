import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { useAnnotationLabels, useCreateAnnotation, useDeleteAnnotation } from '$lib/hooks';
import { toast } from 'svelte-sonner';

/**
 * Moves an annotation to another annotation source by copying it there and deleting the
 * original. The copy keeps the class, type, parent sample and geometry, but not the confidence.
 * When the delete fails, the copy stays and the original is reported as still there. A move
 * that starts while another runs does nothing.
 */
export const useMoveAnnotationByCopy = (getCollectionId: () => string) => {
    const labels = useAnnotationLabels(() => ({ collectionId: getCollectionId() }));
    const { createAnnotation } = useCreateAnnotation({ getCollectionId });
    const { deleteAnnotation } = useDeleteAnnotation({ getCollectionId });
    let isMoving = $state(false);

    /** The ID of the copy, or null when nothing was copied. */
    const moveByCopy = async (
        annotation: AnnotationView,
        sourceName: string
    ): Promise<string | null> => {
        if (isMoving) return null;
        const labelName = annotation.annotation_label.annotation_label_name;
        const label = labels.data?.find((label) => label.annotation_label_name === labelName);
        if (!label?.annotation_label_id) {
            toast.error('Annotation classes are still loading. Please try again.');
            return null;
        }
        isMoving = true;
        try {
            return await copyThenDelete(annotation, sourceName, label.annotation_label_id);
        } finally {
            isMoving = false;
        }
    };

    const copyThenDelete = async (
        annotation: AnnotationView,
        sourceName: string,
        labelId: string
    ): Promise<string | null> => {
        let copyId: string;
        try {
            const copy = await createAnnotation({
                annotation_label_id: labelId,
                annotation_type: annotation.annotation_type,
                annotation_collection_name: sourceName,
                parent_sample_id: annotation.parent_sample_id,
                ...annotation.object_detection_details,
                ...annotation.segmentation_details
            });
            copyId = copy.sample_id;
        } catch {
            toast.error('Could not move the annotation. Please try again.');
            return null;
        }
        try {
            await deleteAnnotation(annotation.sample_id, annotation.annotation_type);
        } catch {
            toast.error(`Copied to ${sourceName}, but the original is still there.`);
        }
        return copyId;
    };

    return {
        moveByCopy,
        get isMoving() {
            return isMoving;
        }
    };
};
