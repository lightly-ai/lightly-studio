import { useUpdateAnnotationsMutation } from '$lib/hooks';
import { toast } from 'svelte-sonner';
import type {
    AnnotationUpdateInput,
    AnnotationView,
    Cuboid3dCreate
} from '$lib/api/lightly_studio_local';
import type { CuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/domain';
import type { ReversibleAction } from '$lib/hooks/useReversibleActions';
import { addCuboidGeometryChangeToUndoStack } from '$lib/services/addCuboidGeometryChangeToUndoStack';
import type { AnnotationIdMap } from '../cuboidUndo';

interface Params {
    getCollectionId: () => string | undefined;
    onUpdated: () => Promise<unknown>;
    /** The persisted annotations of the active tick. */
    getAnnotations: () => readonly AnnotationView[];
    annotationIds: AnnotationIdMap;
    addReversibleAction: (action: ReversibleAction) => void;
    /** Runs before an undo saves the previous geometry of the cuboid. */
    onRestore: (annotationId: string) => void;
}

interface CuboidTransform extends Pick<
    CuboidAnnotation,
    'frameId' | 'center' | 'rotation' | 'size'
> {
    annotationId: string;
}

interface UseUpdateCuboidAnnotationReturn {
    handleCuboidTransform: (transform: CuboidTransform) => Promise<boolean>;
    /** Resolves when the saves of the cuboid that already started are complete. */
    waitForSaves: (annotationId: string) => Promise<void>;
}

function buildCuboidInput({ frameId, center, rotation, size }: CuboidTransform): Cuboid3dCreate {
    const [px, py, pz] = center;
    const [qx, qy, qz, qw] = rotation;
    const [sx, sy, sz] = size;
    return { frame_id: frameId, px, py, pz, qx, qy, qz, qw, sx, sy, sz };
}

/** Saves cuboid geometry, refreshes the workspace, and adds the undo of each save. */
export function useUpdateCuboidAnnotation({
    getCollectionId,
    onUpdated,
    getAnnotations,
    annotationIds,
    addReversibleAction,
    onRestore
}: Params): UseUpdateCuboidAnnotationReturn {
    const { updateAnnotations } = useUpdateAnnotationsMutation({
        getCollectionId: () => getCollectionId() ?? ''
    });

    // Serializes saves per cuboid so that rapid successive drags cannot persist out of order.
    const saves = new Map<string, Promise<unknown>>();
    // Saved geometry that the persisted annotations do not show yet, because a refresh failed.
    const unrefreshedCuboids = new Map<string, Cuboid3dCreate>();

    async function refreshAnnotations(): Promise<void> {
        try {
            await onUpdated();
            unrefreshedCuboids.clear();
        } catch {
            toast.error(
                'Annotation updated, but the workspace could not refresh. Please try again.'
            );
        }
    }

    async function saveCuboid(
        collectionId: string | undefined,
        annotationId: string,
        cuboid: Cuboid3dCreate
    ): Promise<boolean> {
        if (!collectionId) return false;
        const input: AnnotationUpdateInput = {
            annotation_id: annotationId,
            collection_id: collectionId,
            cuboid_3d: cuboid
        };
        try {
            await updateAnnotations([input], collectionId);
        } catch {
            toast.error('Failed to update annotation. Please try again.');
            // Refetch so the viewport reverts to the last persisted geometry.
            await refreshAnnotations();
            return false;
        }
        unrefreshedCuboids.set(annotationId, cuboid);
        await refreshAnnotations();
        return true;
    }

    function findSavedCuboid(annotationId: string): Cuboid3dCreate | undefined {
        const unrefreshedCuboid = unrefreshedCuboids.get(annotationId);
        if (unrefreshedCuboid) return unrefreshedCuboid;
        const annotation = getAnnotations().find(({ sample_id }) => sample_id === annotationId);
        return annotation?.cuboid_3d_details ?? undefined;
    }

    function enqueueSave(annotationId: string, save: () => Promise<boolean>): Promise<boolean> {
        const previousSave = saves.get(annotationId) ?? Promise.resolve();
        // Chain after previous save; absorb its error so this save always runs.
        const thisSave = previousSave.catch(() => {}).then(save);
        saves.set(annotationId, thisSave);
        return thisSave;
    }

    async function waitForSaves(annotationId: string): Promise<void> {
        await Promise.allSettled([saves.get(annotationId)]);
    }

    function restoreGeometry(
        collectionId: string | undefined,
        annotationId: string,
        cuboid: Cuboid3dCreate
    ): Promise<boolean> {
        const currentId = annotationIds.resolve(annotationId);
        onRestore(currentId);
        return enqueueSave(currentId, () => saveCuboid(collectionId, currentId, cuboid));
    }

    async function saveTransform(transform: CuboidTransform): Promise<boolean> {
        // The undo uses the collection of the save, also after the workspace changes it.
        const collectionId = getCollectionId();
        // Saves of one cuboid run in sequence, so this is the geometry of the previous save.
        const previousCuboid = findSavedCuboid(transform.annotationId);
        const saved = await saveCuboid(
            collectionId,
            transform.annotationId,
            buildCuboidInput(transform)
        );
        if (saved && previousCuboid) {
            addCuboidGeometryChangeToUndoStack({
                annotationId: transform.annotationId,
                previousCuboid,
                addReversibleAction,
                restoreGeometry: (annotationId, cuboid) =>
                    restoreGeometry(collectionId, annotationId, cuboid)
            });
        }
        return saved;
    }

    function handleCuboidTransform(transform: CuboidTransform): Promise<boolean> {
        return enqueueSave(transform.annotationId, () => saveTransform(transform));
    }

    return { handleCuboidTransform, waitForSaves };
}
