import type { AnnotationView } from '$lib/api/lightly_studio_local';
import type { ReversibleAction } from '$lib/hooks/useReversibleActions';

export const ANNOTATION_CREATE_GROUP_ID = 'annotation-create';

export const addAnnotationCreateToUndoStack = ({
    annotation,
    addReversibleAction,
    deleteAnnotation,
    refetch
}: {
    annotation: AnnotationView;
    addReversibleAction: (action: ReversibleAction) => void;
    deleteAnnotation: (annotationId: string) => Promise<void>;
    refetch: () => void;
}) => {
    const execute = async () => {
        await deleteAnnotation(annotation.sample_id);
        refetch();
    };

    addReversibleAction({
        id: `annotation-create-${annotation.sample_id}-${Date.now()}`,
        description: `Undo create annotation`,
        execute,
        timestamp: new Date(),
        groupId: ANNOTATION_CREATE_GROUP_ID
    });
};
