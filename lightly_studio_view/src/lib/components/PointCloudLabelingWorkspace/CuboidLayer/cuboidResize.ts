import { Plane, Quaternion, Vector3 } from 'three';
import type {
    CuboidAnnotation,
    CuboidHandle,
    Quaternion as DomainQuaternion
} from '$lib/components/PointCloudLabelingWorkspace/domain';

/** Axis index and signed direction for a face handle. */
interface FaceAxis {
    /** 0 = x, 1 = y, 2 = z. */
    readonly axis: 0 | 1 | 2;
    /** +1 for the max face, -1 for the min face. */
    readonly sign: 1 | -1;
}

/**
 * Returns the local axis and direction for a face handle.
 *
 * @param handle - One of the six face resize handles.
 * @returns Axis index and sign for the handle.
 */
export function getFaceAxis(handle: CuboidHandle): FaceAxis {
    switch (handle) {
        case 'max-x':
            return { axis: 0, sign: 1 };
        case 'min-x':
            return { axis: 0, sign: -1 };
        case 'max-y':
            return { axis: 1, sign: 1 };
        case 'min-y':
            return { axis: 1, sign: -1 };
        case 'max-z':
            return { axis: 2, sign: 1 };
        case 'min-z':
            return { axis: 2, sign: -1 };
        default:
            throw new Error(`getFaceAxis: "${handle}" is not a face handle`);
    }
}

/**
 * Computes the world-space face normal for a handle, accounting for cuboid rotation.
 *
 * @param handle - Face handle identifying the axis and direction.
 * @param rotation - Cuboid orientation as a unit xyzw quaternion.
 * @returns Normalised world-space direction vector for the face.
 */
export function getWorldFaceNormal(handle: CuboidHandle, rotation: DomainQuaternion): Vector3 {
    const { axis, sign } = getFaceAxis(handle);
    const local = new Vector3();
    local.setComponent(axis, sign);
    return local.applyQuaternion(new Quaternion(...rotation));
}

/**
 * Computes the world-space centre of a cuboid face.
 *
 * @param handle - Face handle identifying which face.
 * @param annotation - Cuboid with center, size, and rotation.
 * @returns World-space position of the face centre.
 */
export function getWorldFaceCenter(handle: CuboidHandle, annotation: CuboidAnnotation): Vector3 {
    const { axis, sign } = getFaceAxis(handle);
    const halfExtent = annotation.size[axis] / 2;
    const localOffset = new Vector3();
    localOffset.setComponent(axis, sign * halfExtent);
    localOffset.applyQuaternion(new Quaternion(...annotation.rotation));
    return new Vector3(...annotation.center).add(localOffset);
}

/**
 * Builds a drag plane for a face handle drag.
 *
 * The plane is perpendicular to the camera view direction and passes through
 * the face centre. Any ray cast from the camera always has a positive component
 * along the view direction, so it always intersects this plane — unlike a plane
 * whose normal is derived from a cross-product with the camera direction, which
 * produces a plane that every camera ray is parallel to.
 *
 * After intersecting the plane, project the delta onto `worldFaceNormal` to
 * obtain the displacement along the face axis.
 *
 * @param cameraDirection - Camera world-space view direction (points into scene).
 * @param faceCenter - World-space position the plane passes through.
 * @returns Three.js plane for pointer ray intersection.
 */
export function buildDragPlane(cameraDirection: Vector3, faceCenter: Vector3): Plane {
    return new Plane().setFromNormalAndCoplanarPoint(cameraDirection, faceCenter);
}

const MIN_SIZE = 1e-6;

/**
 * Applies a resize delta to a cuboid, keeping the opposite face fixed.
 *
 * The dragged face moves by `delta` metres along its face normal; the cuboid
 * centre shifts so the opposite face remains stationary. Size magnitude is
 * clamped to a minimum of 1e-6 m per axis; negative size values are treated
 * as a signed magnitude (sign is preserved, only the magnitude changes).
 *
 * @param cuboid - Original cuboid to resize.
 * @param handle - Face handle determining the axis and direction.
 * @param delta - Signed displacement in metres along the face normal.
 * @returns Updated cuboid annotation with the new size and center.
 */
export function applyResizeDelta(
    cuboid: CuboidAnnotation,
    handle: CuboidHandle,
    delta: number
): CuboidAnnotation {
    const { axis } = getFaceAxis(handle);
    const worldFaceNormal = getWorldFaceNormal(handle, cuboid.rotation);

    const currentSize = cuboid.size[axis];
    const dimensionSign = currentSize < 0 ? -1 : 1;
    const currentMagnitude = Math.abs(currentSize);
    const newMagnitude = Math.max(MIN_SIZE, currentMagnitude + delta);

    // Opposite face position (world) stays fixed; recompute centre from it.
    const oppositeFace = new Vector3(...cuboid.center).addScaledVector(
        worldFaceNormal,
        -currentMagnitude / 2
    );
    const newCenter = oppositeFace.addScaledVector(worldFaceNormal, newMagnitude / 2);

    const size = [...cuboid.size] as [number, number, number];
    size[axis] = dimensionSign * newMagnitude;

    return {
        ...cuboid,
        size,
        center: [newCenter.x, newCenter.y, newCenter.z]
    };
}
