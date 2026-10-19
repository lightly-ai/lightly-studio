import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { useAnnotationLabels, useCreateAnnotation, useDeleteAnnotation } from '$lib/hooks';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { addAnnotationCreateToUndoStack } from '$lib/services/addAnnotationCreateToUndoStack';
import { get, writable } from 'svelte/store';
import { toast } from 'svelte-sonner';

interface Params {
    collectionId: string;
    annotation: AnnotationView;
    onCopied: () => void;
}

export const useCopyAnnotationToSource = (getParams: () => Params) => {
    const labels = useAnnotationLabels(() => ({ collectionId: getParams().collectionId }));
    const getCollectionId = () => getParams().collectionId;
    const { createAnnotation } = useCreateAnnotation({ getCollectionId });
    const { deleteAnnotation } = useDeleteAnnotation({ getCollectionId });
    const { addReversibleAction } = useGlobalStorage();
    const pending = writable(false);
    const copy = async (sourceName: string) => {
        if (get(pending)) return false;
        const { annotation, onCopied, collectionId } = getParams();
        const labelName = annotation.annotation_label.annotation_label_name;
        const label = labels.data?.find((label) => label.annotation_label_name === labelName);
        if (!label?.annotation_label_id) {
            toast.error('Annotation classes are still loading. Please try again.');
            return false;
        }
        pending.set(true);
        try {
            const created = await createAnnotation({
                annotation_label_id: label.annotation_label_id,
                annotation_type: annotation.annotation_type,
                annotation_collection_name: sourceName,
                parent_sample_id: annotation.parent_sample_id,
                ...annotation.object_detection_details,
                ...annotation.segmentation_details
            });
            addAnnotationCreateToUndoStack({
                annotation: created,
                addReversibleAction,
                deleteAnnotation: (id, type) => deleteAnnotation(id, type, collectionId),
                refetch: onCopied
            });
            onCopied();
            return true;
        } catch {
            toast.error('Could not duplicate the annotation. Please try again.');
            return false;
        } finally {
            pending.set(false);
        }
    };
    return { copy, pending };
};
