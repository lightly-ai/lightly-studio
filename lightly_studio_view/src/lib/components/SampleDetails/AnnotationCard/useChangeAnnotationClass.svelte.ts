import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import {
    useAnnotation,
    useGlobalStorage,
    useStickyClass,
    useUpdateAnnotationsMutation
} from '$lib/hooks';
import { addAnnotationLabelChangeToUndoStack } from '$lib/services/addAnnotationLabelChangeToUndoStack';
import { toast } from 'svelte-sonner';

interface Params {
    collectionId: string;
    /** The selected annotation. */
    annotation: AnnotationView;
    refetch: () => void;
}

/**
 * Changes the class of the selected annotation, with undo. The class becomes the class for new
 * annotations too. Call during component init: it reads the annotation label context.
 */
export const useChangeAnnotationClass = (getParams: () => Params) => {
    const getCollectionId = () => getParams().collectionId;
    // Refreshes the annotation, the class list and the counts after a class change.
    const { refetch: refetchAnnotation } = useAnnotation(() => ({
        collectionId: getCollectionId(),
        annotationId: getParams().annotation.sample_id
    }));
    const { updateAnnotations } = useUpdateAnnotationsMutation({ getCollectionId });
    const { addReversibleAction } = useGlobalStorage();
    const { setAnnotationLabel } = useAnnotationLabelContext();
    const { pickClass } = useStickyClass();

    // A second pick while the first request runs would update twice and add two undo entries.
    let isChanging = false;
    // The class of the last change, which the `annotation` prop shows only one refresh later.
    // Without it a second pick reads the class from before the first one.
    let changed: { annotationId: string; className: string } | undefined;
    const changeClass = async (className: string) => {
        const { annotation, collectionId, refetch } = getParams();
        const currentClass =
            changed?.annotationId === annotation.sample_id
                ? changed.className
                : annotation.annotation_label.annotation_label_name;
        if (isChanging || className === currentClass) return;
        isChanging = true;
        try {
            await updateAnnotations([
                {
                    annotation_id: annotation.sample_id,
                    collection_id: collectionId,
                    label_name: className
                }
            ]);
            changed = { annotationId: annotation.sample_id, className };
            // Undo restores the class the annotation had before the request.
            addAnnotationLabelChangeToUndoStack({
                annotations: [
                    {
                        sample_id: annotation.sample_id,
                        annotation_label: { annotation_label_name: currentClass }
                    }
                ],
                collectionId,
                addReversibleAction,
                updateAnnotations,
                refresh: refetch
            });
            pickClass(collectionId, className);
            setAnnotationLabel(className);
            refetchAnnotation();
            refetch();
            toast.success('Annotation updated successfully');
        } catch (error) {
            toast.error('Failed to update annotation: ' + (error as Error).message);
        } finally {
            isChanging = false;
        }
    };

    return { changeClass };
};
