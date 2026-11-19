export interface AnnotationIdMap {
    /** Returns the current ID of the annotation that had this ID. */
    resolve(annotationId: string): string;
    /** Records that the annotation with `previousId` now has `currentId`. */
    replace(previousId: string, currentId: string): void;
}

/**
 * Keeps undo entries valid after an undo of a delete re-creates an annotation with a new ID.
 */
export function createAnnotationIdMap(): AnnotationIdMap {
    const currentIds = new Map<string, string>();

    function resolve(annotationId: string): string {
        let currentId = annotationId;
        let nextId = currentIds.get(currentId);
        while (nextId !== undefined) {
            currentId = nextId;
            nextId = currentIds.get(currentId);
        }
        return currentId;
    }

    return {
        resolve,
        replace(previousId, currentId) {
            currentIds.set(previousId, currentId);
        }
    };
}
