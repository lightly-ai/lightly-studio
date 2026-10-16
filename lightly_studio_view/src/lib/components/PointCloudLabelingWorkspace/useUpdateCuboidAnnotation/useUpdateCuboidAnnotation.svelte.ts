import { useUpdateAnnotationsMutation } from '$lib/hooks';
import { toast } from 'svelte-sonner';
import type { AnnotationUpdateInput } from '$lib/api/lightly_studio_local';
import type { CuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/domain';

interface Params {
    getCollectionId: () => string | undefined;
    onUpdated: () => Promise<unknown>;
}

interface CuboidTransform extends Pick<
    CuboidAnnotation,
    'frameId' | 'center' | 'rotation' | 'size'
> {
    annotationId: string;
}

interface UseUpdateCuboidAnnotationReturn {
    handleCuboidTransform: (transform: CuboidTransform) => Promise<boolean>;
}

function buildCuboidInput({
    frameId,
    center,
    rotation,
    size
}: CuboidTransform): NonNullable<AnnotationUpdateInput['cuboid_3d']> {
    const [px, py, pz] = center;
    const [qx, qy, qz, qw] = rotation;
    const [sx, sy, sz] = size;
    return { frame_id: frameId, px, py, pz, qx, qy, qz, qw, sx, sy, sz };
}

/** Saves cuboid geometry and refreshes the annotations displayed in the workspace. */
export function useUpdateCuboidAnnotation({
    getCollectionId,
    onUpdated
}: Params): UseUpdateCuboidAnnotationReturn {
    const { updateAnnotations } = useUpdateAnnotationsMutation({
        getCollectionId: () => getCollectionId() ?? ''
    });

    // Serializes saves per cuboid so that rapid successive drags cannot persist out of order.
    const saves = new Map<string, Promise<unknown>>();


    async function refreshAnnotations(): Promise<void> {
        try {
            await onUpdated();
        } catch {
            toast.error(
                'Annotation updated, but the workspace could not refresh. Please try again.'
            );
        }
    }

    async function doSave(transform: CuboidTransform): Promise<boolean> {
        const collectionId = getCollectionId();
        if (!collectionId) return false;
        const input: AnnotationUpdateInput = {
            annotation_id: transform.annotationId,
            collection_id: collectionId,
            cuboid_3d: buildCuboidInput(transform)
        };
        try {
            await updateAnnotations([input]);
        } catch {
            toast.error('Failed to update annotation. Please try again.');
            // Refetch so the viewport reverts to the last persisted geometry.
            await refreshAnnotations();
            return false;
        }
        await refreshAnnotations();
        return true;
    }

    async function handleCuboidTransform(transform: CuboidTransform): Promise<boolean> {
        const prev = saves.get(transform.annotationId) ?? Promise.resolve();
        // Chain after previous save; absorb its error so this save always runs.
        const thisCall = prev.catch(() => {}).then(() => doSave(transform));
        saves.set(transform.annotationId, thisCall);
        return thisCall;
    }

    return { handleCuboidTransform };
}
