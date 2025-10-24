import { type AnnotationUpdateInput, type AnnotationView } from '$lib/api/lightly_studio_local';
import { getBoundingBox } from '$lib/components/SampleAnnotation/utils';
import type { ReversibleAction } from '$lib/hooks/useReversibleActions';

export const BBOX_CHANGE_ANNOTATION_DETAILS = `bbox-change-annotation-details`;

export const addAnnotationUpdateToUndoStack = ({
    annotation,
    addReversibleAction,
    updateAnnotation
}: {
    annotation: AnnotationView;
    addReversibleAction: (action: ReversibleAction) => void;
    updateAnnotation: (input: AnnotationUpdateInput) => Promise<void>;
}) => {
    const prevBoundingBox = getBoundingBox(annotation);

    const execute = async () => {
        const revertAnnotation = {
            annotation_id: annotation.annotation_id,
            dataset_id: annotation.dataset_id,
            bounding_box: prevBoundingBox
        };

        await updateAnnotation(revertAnnotation);
    };

    addReversibleAction({
        id: `bbox-change-${annotation.annotation_id}-${Date.now()}`,
        description: `Revert bounding box change for annotation ${annotation.annotation_id}`,
        execute,
        timestamp: new Date(),
        groupId: BBOX_CHANGE_ANNOTATION_DETAILS
    });
};
