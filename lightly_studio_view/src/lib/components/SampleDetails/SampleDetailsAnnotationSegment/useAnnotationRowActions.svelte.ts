import { AnnotationType, type AnnotationView } from '$lib/api/lightly_studio_local';
import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import { useDeleteAnnotationWithUndo, useStickyClass } from '$lib/hooks';
import { useAnnotationSelection } from '$lib/hooks/useAnnotationSelection/useAnnotationSelection';

interface UseAnnotationRowActionsParams {
    getCollectionId: () => string;
    /** All annotations of the sample. */
    getAnnotations: () => AnnotationView[];
    getIsPanModeEnabled: () => boolean;
    refetch: () => void;
}

/**
 * What a row of the Annotations panel does: select, lock, delete with undo and relabel its
 * annotation. Call during component init: it reads the annotation label context.
 */
export const useAnnotationRowActions = (params: UseAnnotationRowActionsParams) => {
    const { getCollectionId, getAnnotations } = params;
    const {
        context,
        setAnnotationId,
        setAnnotationLabel,
        setLastCreatedAnnotationId,
        setLockedAnnotationIds
    } = useAnnotationLabelContext();
    const { selectAnnotation } = useAnnotationSelection();
    const { deleteWithUndo } = useDeleteAnnotationWithUndo(getCollectionId);
    const { pickClass } = useStickyClass();

    const select = (annotationId: string) =>
        selectAnnotation({
            annotationId,
            annotations: getAnnotations(),
            collectionId: getCollectionId()
        });

    return {
        select,
        /** A click on the row. A Space pan must not select. */
        toggleSelection: (annotationId: string) => {
            if (!params.getIsPanModeEnabled()) select(annotationId);
        },
        toggleLock: (annotationId: string) => {
            const locked = new Set(context.lockedAnnotationIds);
            if (!locked.delete(annotationId)) locked.add(annotationId);
            setLockedAnnotationIds(locked);
        },
        remove: async (annotation: AnnotationView) => {
            const isDeleted = await deleteWithUndo(annotation, params.refetch);
            if (isDeleted && context.annotationId === annotation.sample_id) setAnnotationId(null);
        },
        // A relabel is an explicit class pick: it becomes the class for new annotations.
        relabel: (annotation: AnnotationView, className: string) => {
            pickClass(getCollectionId(), className);
            setLastCreatedAnnotationId(null);
            if (context.annotationType === AnnotationType.SEGMENTATION_MASK) {
                setAnnotationId(annotation.sample_id);
            }
            if (context.annotationId === annotation.sample_id) setAnnotationLabel(className);
        }
    };
};
