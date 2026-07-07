import type { AnnotationView } from '$lib/api/lightly_studio_local';
import type { ReversibleAction, ReversibleActionCallback } from '$lib/hooks/useReversibleActions';

export const ANNOTATION_CREATE_GROUP_ID = 'annotation-create';

export const addAnnotationCreateToUndoStack = ({
    annotation,
    addReversibleAction,
    deleteAnnotation,
    refetch,
    onUndo,
    onDelete
}: {
    annotation: AnnotationView;
    addReversibleAction: (action: ReversibleAction) => void;
    deleteAnnotation: (annotationId: string) => Promise<void>;
    refetch: () => void;
    onUndo?: ReversibleActionCallback;
    /** Called after deletion succeeds, before refetch. Use to clean up UI state
     *  (e.g. clear the selected annotation ID from context). */
    onDelete?: ReversibleActionCallback;
}) => {
    const execute = async () => {
        await deleteAnnotation(annotation.sample_id);
        await onUndo?.();
        await onDelete?.();
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
