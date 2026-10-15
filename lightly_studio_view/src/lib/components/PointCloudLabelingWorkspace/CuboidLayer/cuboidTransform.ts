import type { Object3D } from 'three';
import type * as Domain from '$lib/components/PointCloudLabelingWorkspace/domain';
import type { useUpdateCuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/useUpdateCuboidAnnotation';

export const GIZMO_MODES: Partial<Record<Domain.WorkspaceTool, 'translate' | 'rotate' | 'scale'>> =
    {
        translate: 'translate',
        rotate: 'rotate',
        resize: 'scale'
    };

type CuboidTransformPayload = Parameters<
    ReturnType<typeof useUpdateCuboidAnnotation>['handleCuboidTransform']
>[0];

/**
 * Reads the current transform of `obj`, resets its scale to (1,1,1), and returns
 * the cuboid geometry payload ready for `handleCuboidTransform`.
 *
 * @param annotation - The annotation whose geometry is being updated.
 * @param obj - The Three.js object after the gizmo has mutated it.
 * @returns The new geometry expressed in the annotation-update domain type.
 */
export function buildCuboidTransformPayload(
    annotation: Domain.CuboidAnnotation,
    obj: Object3D
): CuboidTransformPayload {
    const center: Domain.Vector3 = [obj.position.x, obj.position.y, obj.position.z];
    const q = obj.quaternion;
    const rotation: Domain.Quaternion = [q.x, q.y, q.z, q.w];
    const size: Domain.Vector3 = [
        annotation.size[0] * obj.scale.x,
        annotation.size[1] * obj.scale.y,
        annotation.size[2] * obj.scale.z
    ];
    obj.scale.set(1, 1, 1);
    return { annotationId: annotation.id, frameId: annotation.frameId, center, rotation, size };
}
