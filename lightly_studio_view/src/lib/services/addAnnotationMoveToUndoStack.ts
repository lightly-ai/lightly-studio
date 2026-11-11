import type {
    AnnotationCreateInput,
    CreateAnnotationResponse
} from '$lib/api/lightly_studio_local';
import type { ReversibleAction } from '$lib/hooks/useReversibleActions';

export const ANNOTATION_MOVE_GROUP_ID = 'annotation-move';

/**
 * Adds the undo of a move by copy. It re-creates the original in its source first, then deletes
 * the copy, so a failed step leaves both annotations instead of none. The re-created original
 * gets a new ID, and like the undo of a delete it has no confidence.
 */
export const addAnnotationMoveToUndoStack = ({
    copy,
    original,
    addReversibleAction,
    createAnnotation,
    deleteAnnotation,
    refetch
}: {
    copy: { sample_id: string; annotation_type: string };
    /** The original as it was, or null when the move could not delete it. */
    original: AnnotationCreateInput | null;
    addReversibleAction: (action: ReversibleAction) => void;
    createAnnotation: (input: AnnotationCreateInput) => Promise<CreateAnnotationResponse>;
    deleteAnnotation: (annotationId: string, annotationType: string) => Promise<void>;
    refetch: () => void;
}) => {
    const execute = async () => {
        if (original) await createAnnotation(original);
        await deleteAnnotation(copy.sample_id, copy.annotation_type);
        refetch();
    };

    addReversibleAction({
        id: `annotation-move-${copy.sample_id}-${Date.now()}`,
        description: 'Undo move annotation',
        execute,
        timestamp: new Date(),
        groupId: ANNOTATION_MOVE_GROUP_ID
    });
};
