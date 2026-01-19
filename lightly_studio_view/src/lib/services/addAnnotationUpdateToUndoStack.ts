import { type AnnotationUpdateInput, type AnnotationView } from '$lib/api/lightly_studio_local';
import { getBoundingBox } from '$lib/components/SampleAnnotation/utils';
import type { ReversibleAction } from '$lib/hooks/useReversibleActions';

export const BBOX_CHANGE_ANNOTATION_DETAILS = `bbox-change-annotation-details`;

export const addAnnotationUpdateToUndoStack = ({
    annotation,
    collection_id,
    addReversibleAction,
    updateAnnotation
}: {
    annotation: AnnotationView;
    collection_id: string;
    addReversibleAction: (action: ReversibleAction) => void;
    updateAnnotation: (input: AnnotationUpdateInput) => Promise<void>;
}) => {
    const prevBoundingBox = getBoundingBox(annotation);

    const execute = async () => {
        const revertAnnotation = {
            annotation_id: annotation.sample_id,
            collection_id: collection_id,
            bounding_box: prevBoundingBox,
            segmentation_mask: annotation?.segmentation_details?.segmentation_mask
        };

        await updateAnnotation(revertAnnotation);
    };

    addReversibleAction({
        id: `bbox-change-${annotation.sample_id}-${Date.now()}`,
        description: `Revert bounding box change for annotation ${annotation.sample_id}`,
        execute,
        timestamp: new Date(),
        groupId: BBOX_CHANGE_ANNOTATION_DETAILS
    });
};
