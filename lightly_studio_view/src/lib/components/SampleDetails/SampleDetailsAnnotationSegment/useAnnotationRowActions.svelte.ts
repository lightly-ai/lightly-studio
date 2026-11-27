import { AnnotationType, type AnnotationView } from '$lib/api/lightly_studio_local';
import { useAnnotationLabelContext, useDeleteAnnotationWithUndo, useStickyClass } from '$lib/hooks';
import { useAnnotationSelection } from '$lib/hooks/useAnnotationSelection/useAnnotationSelection';

interface UseAnnotationRowActionsParams {
    getCollectionId: () => string;
    /** All annotations of the sample. */
    getAnnotations: () => AnnotationView[];
    getIsPanModeEnabled: () => boolean;
    refetch: () => void;
}

interface UseAnnotationRowActionsReturn {
    select: (annotationId: string) => void;
    /** A click on the row. A Space pan must not select. */
    toggleSelection: (annotationId: string) => void;
    remove: (annotation: AnnotationView) => Promise<void>;
    /** A relabel is an explicit class pick: it becomes the class for new annotations. */
    relabel: (annotation: AnnotationView, className: string) => void;
}

/**
 * What a row of the Annotations panel does: select, delete with undo and relabel its
 * annotation. Call during component init: it reads the annotation label context.
 */
export const useAnnotationRowActions = (
    params: UseAnnotationRowActionsParams
): UseAnnotationRowActionsReturn => {
    const { getCollectionId, getAnnotations } = params;
    const { context, setAnnotationId, setAnnotationLabel, setLastCreatedAnnotationId } =
        useAnnotationLabelContext();
    const { selectAnnotation } = useAnnotationSelection();
    const { deleteWithUndo } = useDeleteAnnotationWithUndo(getCollectionId);
    const { pickClass } = useStickyClass();

    const select = (annotationId: string) =>
        selectAnnotation({
            annotationId,
            annotations: getAnnotations()
        });

    return {
        select,
        toggleSelection: (annotationId: string) => {
            if (!params.getIsPanModeEnabled()) select(annotationId);
        },
        remove: async (annotation: AnnotationView) => {
            const isDeleted = await deleteWithUndo(annotation, params.refetch);
            if (isDeleted && context.annotationId === annotation.sample_id) setAnnotationId(null);
        },
        relabel: (annotation: AnnotationView, className: string) => {
            pickClass(getCollectionId(), className);
            setAnnotationLabel(className);
            setLastCreatedAnnotationId(null);
            if (context.annotationType === AnnotationType.SEGMENTATION_MASK) {
                setAnnotationId(annotation.sample_id);
            }
        }
    };
};
