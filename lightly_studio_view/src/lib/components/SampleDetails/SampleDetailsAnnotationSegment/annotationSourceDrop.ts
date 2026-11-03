import type { AnnotationCollectionView } from '$lib/api/lightly_studio_local';

/** Drag data type of an annotation row. Browsers only start a drag that carries data. */
export const ANNOTATION_DRAG_TYPE = 'application/x-lightly-annotation-id';

export interface DraggedAnnotation {
    annotationId: string;
    sourceId: string;
}

interface DropSource {
    id: string;
    name: string;
}

interface SourceDropMove {
    annotationIds: string[];
    sourceName: string;
}

/**
 * Returns the move that dropping the dragged annotation on a source triggers, or null when
 * the drop does nothing: no drag is active, the source is unknown, or it is the annotation's
 * own source.
 */
export const getSourceDropMove = (
    dragged: DraggedAnnotation | null,
    target: DropSource | undefined
): SourceDropMove | null => {
    if (!dragged || !target || dragged.sourceId === target.id) return null;
    return { annotationIds: [dragged.annotationId], sourceName: target.name };
};

/** Looks up a source by ID. Groups of unknown sources have no name to move to. */
export const findDropSource = (
    sources: AnnotationCollectionView[],
    sourceId: string
): DropSource | undefined => {
    const source = sources.find((candidate) => candidate.collection_id === sourceId);
    return source ? { id: source.collection_id, name: source.name } : undefined;
};
