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
    handleCuboidTransform: (transform: CuboidTransform) => Promise<void>;
}

function buildCuboidInput({ frameId, center, rotation, size }: CuboidTransform) {
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

    async function refreshAnnotations(): Promise<void> {
        try {
            await onUpdated();
        } catch {
            toast.error(
                'Annotation updated, but the workspace could not refresh. Please try again.'
            );
        }
    }

    async function handleCuboidTransform(transform: CuboidTransform): Promise<void> {
        const collectionId = getCollectionId();
        if (!collectionId) return;
        const input: AnnotationUpdateInput = {
            annotation_id: transform.annotationId,
            collection_id: collectionId,
            cuboid_3d: buildCuboidInput(transform)
        };
        try {
            await updateAnnotations([input]);
        } catch {
            toast.error('Failed to update annotation. Please try again.');
            return;
        }
        await refreshAnnotations();
    }

    return { handleCuboidTransform };
}
