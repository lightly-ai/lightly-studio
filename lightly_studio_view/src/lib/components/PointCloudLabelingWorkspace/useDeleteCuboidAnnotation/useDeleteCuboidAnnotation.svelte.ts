import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { useDeleteAnnotationWithUndo } from '$lib/hooks';
import type { AnnotationIdMap } from '../cuboidUndo';

interface Params {
    getCollectionId: () => string | undefined;
    getAnnotations: () => readonly AnnotationView[];
    annotationIds: AnnotationIdMap;
    /** Refreshes the workspace after a delete and after its undo. */
    refresh: () => Promise<unknown>;
}

interface UseDeleteCuboidAnnotationReturn {
    handleDeleteCuboid: (cuboidId: string) => Promise<boolean>;
}

/** Deletes a cuboid and adds the undo that restores it with its geometry and track. */
export function useDeleteCuboidAnnotation({
    getCollectionId,
    getAnnotations,
    annotationIds,
    refresh
}: Params): UseDeleteCuboidAnnotationReturn {
    const { deleteWithUndo } = useDeleteAnnotationWithUndo(() => getCollectionId() ?? '');

    async function handleDeleteCuboid(cuboidId: string): Promise<boolean> {
        const annotation = getAnnotations().find(({ sample_id }) => sample_id === cuboidId);
        if (!annotation) return false;
        return deleteWithUndo(annotation, refresh, (restored) =>
            annotationIds.replace(cuboidId, restored.sample_id)
        );
    }

    return { handleDeleteCuboid };
}
