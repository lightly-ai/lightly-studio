import type { Bounds3, CameraMode, Vector3 } from '../../domain';
import { computeGroundPlaneLayout } from '../groundPlaneLayout';

/** Defines creation plane shared by this module. */
interface CreationPlane {
    /** World-space center of the placement plane. */
    center: Vector3;
    /** XYZ Euler rotation that orients the plane toward the camera. */
    rotation: Vector3;
    /** World-space width and height of the placement plane. */
    size: number;
}

/** Uses the ground in 3D/top views and the scene's depth midpoint in side/front views. */
export function getCuboidCreationPlane(
    bounds: Bounds3,
    cameraMode: CameraMode
): CreationPlane | null {
    const extents = bounds.max.map((value, axis) => value - bounds.min[axis]);
    const size = Math.max(...extents) * 10;
    if (size <= 0) return null;
    if (cameraMode === 'perspective' || cameraMode === 'top') {
        const ground = computeGroundPlaneLayout(bounds);
        return ground ? { center: ground.center, rotation: [0, 0, 0], size } : null;
    }
    return {
        center: [
            (bounds.min[0] + bounds.max[0]) / 2,
            (bounds.min[1] + bounds.max[1]) / 2,
            (bounds.min[2] + bounds.max[2]) / 2
        ],
        rotation: cameraMode === 'side' ? [0, Math.PI / 2, 0] : [Math.PI / 2, 0, 0],
        size
    };
}
