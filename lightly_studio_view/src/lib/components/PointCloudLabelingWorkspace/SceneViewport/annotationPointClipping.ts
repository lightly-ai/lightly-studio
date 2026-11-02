import { Plane, Quaternion, Vector3 } from 'three';
import type { CameraMode, CuboidAnnotation } from '../domain';

/** Keeps nearby context within half a meter of the selected cuboid's faces. */
export function getAnnotationPointClipping(
    cameraMode: CameraMode,
    annotation: CuboidAnnotation | undefined
): Plane[] {
    if (cameraMode === 'perspective' || !annotation) return [];
    const rotation = new Quaternion(...annotation.rotation);
    const center = new Vector3(...annotation.center);
    return [0, 1, 2].flatMap((axis) =>
        [-1, 1].map((sign) => {
            const normal = new Vector3().setComponent(axis, sign).applyQuaternion(rotation);
            const extent = annotation.size[axis] / 2 + 0.5;
            return new Plane(normal, extent - normal.dot(center));
        })
    );
}
