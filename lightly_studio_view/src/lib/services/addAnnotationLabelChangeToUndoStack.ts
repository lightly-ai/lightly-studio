import type { AnnotationUpdateInput } from '$lib/api/lightly_studio_local';
import type { ReversibleAction } from '$lib/hooks/useReversibleActions';

export const ANNOTATION_LABEL_CHANGE_GROUP_ID = 'annotation-label-change';

interface AnnotationWithLabel {
    sample_id: string;
    annotation_label: {
        annotation_label_name: string;
    };
}

export const addAnnotationLabelChangeToUndoStack = ({
    annotations,
    collectionId,
    addReversibleAction,
    updateAnnotations,
    refresh
}: {
    annotations: AnnotationWithLabel[];
    collectionId: string;
    addReversibleAction: (action: ReversibleAction) => void;
    updateAnnotations: (inputs: AnnotationUpdateInput[]) => Promise<void>;
    refresh: () => void;
}) => {
    const previousLabels = annotations.map((annotation) => ({
        annotation_id: annotation.sample_id,
        label_name: annotation.annotation_label.annotation_label_name,
        collection_id: collectionId
    }));

    const execute = async () => {
        await updateAnnotations(previousLabels);
        refresh();
    };

    const count = annotations.length;
    addReversibleAction({
        id: `annotation-label-change-${Date.now()}`,
        description: `Undo label change for ${count} annotation${count > 1 ? 's' : ''}`,
        execute,
        timestamp: new Date(),
        groupId: ANNOTATION_LABEL_CHANGE_GROUP_ID
    });
};
