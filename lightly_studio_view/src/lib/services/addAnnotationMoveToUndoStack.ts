import type {
    AnnotationCreateInput,
    CreateAnnotationResponse
} from '$lib/api/lightly_studio_local';
import type { ReversibleAction } from '$lib/hooks/useReversibleActions';

export const ANNOTATION_MOVE_GROUP_ID = 'annotation-move';

// The ID an undone move gave the re-created original, by the ID the original had before. The undo
// of an earlier move of the same annotation holds the ID from before, and reads the new one here.
// An entry is dropped once that earlier undo has used it.
const replacementIds = new Map<string, string>();

/**
 * Adds the undo of a move by copy. It re-creates the original in its source first, then deletes
 * the copy, so a failed step leaves both annotations instead of none. The re-created original
 * gets a new ID, and like the undo of a delete it has no confidence.
 */
export const addAnnotationMoveToUndoStack = ({
    copy,
    original,
    originalId,
    addReversibleAction,
    createAnnotation,
    deleteAnnotation,
    refetch
}: {
    copy: { sample_id: string; annotation_type: string };
    /** The original as it was, or null when the move could not delete it. */
    original: AnnotationCreateInput | null;
    /** The ID of the original, which the undo of an earlier move of it still holds. */
    originalId: string;
    addReversibleAction: (action: ReversibleAction) => void;
    createAnnotation: (input: AnnotationCreateInput) => Promise<CreateAnnotationResponse>;
    deleteAnnotation: (annotationId: string, annotationType: string) => Promise<void>;
    refetch: () => void;
}) => {
    // A failed delete leaves the action on the stack, and a retry must not create a second
    // original.
    let isOriginalRecreated = false;
    const execute = async () => {
        if (original && !isOriginalRecreated) {
            const recreated = await createAnnotation(original);
            isOriginalRecreated = true;
            replacementIds.set(originalId, recreated.sample_id);
        }
        const copyId = replacementIds.get(copy.sample_id) ?? copy.sample_id;
        await deleteAnnotation(copyId, copy.annotation_type);
        replacementIds.delete(copy.sample_id);
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
