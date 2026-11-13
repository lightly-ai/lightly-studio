import type { Object3D } from 'three';
import type * as Domain from '$lib/components/PointCloudLabelingWorkspace/domain';
import type { useUpdateCuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/useUpdateCuboidAnnotation';
import { MIN_CUBOID_SIZE } from './CuboidFaceResize/cuboidFaceResize';

export function captureTransformSnapshot(obj: Object3D) {
    return {
        position: obj.position.clone(),
        quaternion: obj.quaternion.clone(),
        scale: obj.scale.clone()
    };
}

export function restoreTransformSnapshot(
    obj: Object3D,
    snapshot: ReturnType<typeof captureTransformSnapshot>
): void {
    obj.position.copy(snapshot.position);
    obj.quaternion.copy(snapshot.quaternion);
    obj.scale.copy(snapshot.scale);
}

const EDIT_MODES = ['translate', 'rotate', 'resize'] as const;

/**
 * Returns the edit handles to show on a selected cuboid. Orthographic views show all
 * handles at once while any edit tool is active; perspective shows only the active one.
 */
export function getCuboidEditModes(
    tool: Domain.WorkspaceTool,
    cameraMode: Domain.CameraMode
): (typeof EDIT_MODES)[number][] {
    const editMode = EDIT_MODES.find((mode) => mode === tool);
    if (!editMode) return [];
    return cameraMode === 'perspective' ? [editMode] : [...EDIT_MODES];
}

export function getCuboidGizmoOptions(mode: string, cameraMode: Domain.CameraMode) {
    if (cameraMode === 'perspective') {
        return { space: 'local' as const, showX: true, showY: true, showZ: true };
    }
    // Rotate shows only the axis facing the camera; translate shows the two in-plane axes.
    const showFacingAxis = mode === 'rotate';
    return {
        space: 'world' as const,
        showX: (cameraMode === 'side') === showFacingAxis,
        showY: (cameraMode === 'front') === showFacingAxis,
        showZ: (cameraMode === 'top') === showFacingAxis
    };
}

type CuboidTransformPayload = Parameters<
    ReturnType<typeof useUpdateCuboidAnnotation>['handleCuboidTransform']
>[0];

/**
 * Reads the current transform of `obj`, resets its scale to (1,1,1), and returns
 * the cuboid geometry payload ready for `handleCuboidTransform`.
 *
 * @param annotation - The annotation whose geometry is being updated.
 * @param obj - The Three.js object after the gizmo has mutated it.
 * @param currentSize - Optional working size to use instead of annotation.size.
 *   Pass the size from a previous resize so successive drags accumulate correctly
 *   before the refreshed annotation data arrives.
 * @returns The new geometry expressed in the annotation-update domain type.
 */
export function buildCuboidTransformPayload(
    annotation: Domain.CuboidAnnotation,
    obj: Object3D,
    currentSize?: Domain.Vector3
): CuboidTransformPayload {
    const center: Domain.Vector3 = [obj.position.x, obj.position.y, obj.position.z];
    const q = obj.quaternion;
    const rotation: Domain.Quaternion = [q.x, q.y, q.z, q.w];
    const baseSize = currentSize ?? annotation.size;
    const size: Domain.Vector3 = [
        Math.max(baseSize[0] * obj.scale.x, MIN_CUBOID_SIZE),
        Math.max(baseSize[1] * obj.scale.y, MIN_CUBOID_SIZE),
        Math.max(baseSize[2] * obj.scale.z, MIN_CUBOID_SIZE)
    ];
    obj.scale.set(1, 1, 1);
    return { annotationId: annotation.id, frameId: annotation.frameId, center, rotation, size };
}
