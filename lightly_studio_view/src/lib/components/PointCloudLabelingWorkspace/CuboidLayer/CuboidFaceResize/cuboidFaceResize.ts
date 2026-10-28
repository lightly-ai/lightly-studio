import type {
    CameraMode,
    Quaternion,
    Vector3
} from '$lib/components/PointCloudLabelingWorkspace/domain';

/** Minimum allowed cuboid dimension in meters. */
export const MIN_CUBOID_SIZE = 0.01;

/** Identifies which face of the cuboid is being resized. */
interface FaceDefinition {
    axis: 0 | 1 | 2;
    sign: 1 | -1;
    /** Euler XYZ rotation (radians) that orients a PlaneGeometry to face outward on this face. */
    euler: readonly [number, number, number];
}

const PI_2 = Math.PI / 2;
const PI = Math.PI;

export const FACE_DEFINITIONS: readonly FaceDefinition[] = [
    { axis: 0, sign: 1, euler: [0, PI_2, 0] }, // +X
    { axis: 0, sign: -1, euler: [0, -PI_2, 0] }, // -X
    { axis: 1, sign: 1, euler: [-PI_2, 0, 0] }, // +Y
    { axis: 1, sign: -1, euler: [PI_2, 0, 0] }, // -Y
    { axis: 2, sign: 1, euler: [0, 0, 0] }, // +Z
    { axis: 2, sign: -1, euler: [PI, 0, 0] } // -Z
] as const;

/** Orthographic views expose exactly the four faces of the shown rectangle. */
export function getEditableCuboidFaces(cameraMode: CameraMode) {
    if (cameraMode === 'perspective') return FACE_DEFINITIONS;
    const depthAxis = ({ top: 2, side: 1, front: 0 } as const)[cameraMode];
    return FACE_DEFINITIONS.filter((face) => face.axis !== depthAxis);
}

interface FaceNormalParams extends Pick<FaceDefinition, 'axis' | 'sign'> {
    rotation: Quaternion;
}

/**
 * Rotates the local face normal into world space using the cuboid's quaternion.
 *
 * @param axis - The local axis (0=x, 1=y, 2=z) of the face normal.
 * @param sign - The direction along the axis (1 = positive, -1 = negative).
 * @param rotation - The cuboid's unit quaternion in xyzw order.
 * @returns The face's outward normal in world space as a unit vector.
 */
export function computeFaceNormalWorld({ axis, sign, rotation }: FaceNormalParams): Vector3 {
    const [qx, qy, qz, qw] = rotation;
    const nx = axis === 0 ? sign : 0;
    const ny = axis === 1 ? sign : 0;
    const nz = axis === 2 ? sign : 0;

    // q × v
    const cx = qy * nz - qz * ny;
    const cy = qz * nx - qx * nz;
    const cz = qx * ny - qy * nx;

    // q × (q × v)
    const cx2 = qy * cz - qz * cy;
    const cy2 = qz * cx - qx * cz;
    const cz2 = qx * cy - qy * cx;

    // v' = v + 2qw*(q × v) + 2*(q × (q × v))
    return [nx + 2 * qw * cx + 2 * cx2, ny + 2 * qw * cy + 2 * cy2, nz + 2 * qw * cz + 2 * cz2];
}

interface ResizeTransform {
    center: readonly [number, number, number];
    size: readonly [number, number, number];
}

interface ResizeParams {
    originalCenter: Vector3;
    originalSize: Vector3;
    axis: FaceDefinition['axis'];
    faceNormalWorld: Vector3;
    delta: number;
}

interface FaceLayoutParams {
    face: FaceDefinition;
    size: Vector3;
}

interface FaceLayout {
    position: [number, number, number];
    planeSize: [number, number];
}

export function getCuboidFaceLayout({ face, size }: FaceLayoutParams): FaceLayout {
    const position: [number, number, number] = [0, 0, 0];
    position[face.axis] = (face.sign * size[face.axis]) / 2;
    const [width, height, depth] = size;
    const planeSizes: FaceLayout['planeSize'][] = [
        [depth, height],
        [width, depth],
        [width, height]
    ];
    return { position, planeSize: planeSizes[face.axis] };
}

/**
 * Computes new cuboid geometry after dragging one face outward by `delta` world-space meters.
 * The opposite face stays fixed — only the dragged face moves.
 *
 * @param originalCenter - Cuboid center before the drag.
 * @param originalSize - Cuboid full extents before the drag.
 * @param axis - Local axis (0=x, 1=y, 2=z) of the dragged face.
 * @param faceNormalWorld - The face's outward normal in world space.
 * @param delta - Signed meters along `faceNormalWorld` (positive = expanding).
 * @returns New center and size with the opposite face fixed.
 */
export function computeResizedCuboid({
    originalCenter,
    originalSize,
    axis,
    faceNormalWorld,
    delta
}: ResizeParams): ResizeTransform {
    const newSizeAxis = Math.max(originalSize[axis] + delta, MIN_CUBOID_SIZE);
    const actualDelta = newSizeAxis - originalSize[axis];

    const newSize: [number, number, number] = [originalSize[0], originalSize[1], originalSize[2]];
    newSize[axis] = newSizeAxis;

    const newCenter: [number, number, number] = [
        originalCenter[0] + faceNormalWorld[0] * (actualDelta / 2),
        originalCenter[1] + faceNormalWorld[1] * (actualDelta / 2),
        originalCenter[2] + faceNormalWorld[2] * (actualDelta / 2)
    ];

    return { center: newCenter, size: newSize };
}
