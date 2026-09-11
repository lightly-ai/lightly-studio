import type { Quaternion, Vector3 } from '../domain';

/** Row-major 3x3 rotation. */
type Matrix3 = readonly [number, number, number, number, number, number, number, number, number];

/** A pose: `p_parent = rotation * p_child + translation`, in meters. */
export interface RigidTransform {
    readonly rotation: Matrix3;
    readonly translation: Vector3;
}

export const IDENTITY_TRANSFORM: RigidTransform = Object.freeze({
    rotation: Object.freeze([1, 0, 0, 0, 1, 0, 0, 0, 1]) as Matrix3,
    translation: Object.freeze([0, 0, 0]) as Vector3
});

/**
 * Builds a transform from a ROS translation and an xyzw quaternion.
 *
 * @returns The transform, or null when the input cannot describe a rotation -- a
 * non-finite component or a zero-length quaternion. A caller drops that edge rather than
 * placing points by a guess.
 */
export function rigidTransform(translation: Vector3, rotation: Quaternion): RigidTransform | null {
    if (![...translation, ...rotation].every(Number.isFinite)) return null;
    const [qx, qy, qz, qw] = rotation;
    const length = Math.hypot(qx, qy, qz, qw);
    if (length === 0) return null;
    const [x, y, z, w] = [qx / length, qy / length, qz / length, qw / length];
    return {
        rotation: [
            1 - 2 * (y * y + z * z),
            2 * (x * y - z * w),
            2 * (x * z + y * w),
            2 * (x * y + z * w),
            1 - 2 * (x * x + z * z),
            2 * (y * z - x * w),
            2 * (x * z - y * w),
            2 * (y * z + x * w),
            1 - 2 * (x * x + y * y)
        ],
        translation: [translation[0], translation[1], translation[2]]
    };
}

/** `outer * inner`: the transform of `inner`'s child into `outer`'s parent. */
export function composeTransforms(outer: RigidTransform, inner: RigidTransform): RigidTransform {
    const rotation = [0, 1, 2].flatMap((row) =>
        [0, 1, 2].map(
            (column) =>
                outer.rotation[row * 3] * inner.rotation[column] +
                outer.rotation[row * 3 + 1] * inner.rotation[3 + column] +
                outer.rotation[row * 3 + 2] * inner.rotation[6 + column]
        )
    ) as unknown as Matrix3;
    return { rotation, translation: applyTransform(outer, inner.translation) };
}

/** The inverse pose: a rigid transform inverts by transposing and re-projecting. */
export function invertTransform(transform: RigidTransform): RigidTransform {
    const r = transform.rotation;
    const rotation: Matrix3 = [r[0], r[3], r[6], r[1], r[4], r[7], r[2], r[5], r[8]];
    const inverse = { rotation, translation: [0, 0, 0] as Vector3 };
    const [x, y, z] = applyTransform(inverse, transform.translation);
    return { rotation, translation: [-x, -y, -z] };
}

function applyTransform(transform: RigidTransform, point: Vector3): Vector3 {
    const r = transform.rotation;
    const [x, y, z] = point;
    return [
        r[0] * x + r[1] * y + r[2] * z + transform.translation[0],
        r[3] * x + r[4] * y + r[5] * z + transform.translation[1],
        r[6] * x + r[7] * y + r[8] * z + transform.translation[2]
    ];
}

/**
 * Writes `source` into `target` at `at`, transformed, and returns the next write offset.
 *
 * Transforming while copying keeps one pass and one buffer per fused frame, which matters
 * at the point budget: a separate transform step would double both.
 */
export function transformPositionsInto(
    target: Float32Array,
    at: number,
    source: Float32Array,
    transform: RigidTransform
): number {
    const r = transform.rotation;
    const [tx, ty, tz] = transform.translation;
    for (let index = 0; index < source.length; index += 3) {
        const [x, y, z] = [source[index], source[index + 1], source[index + 2]];
        target[at + index] = Math.fround(r[0] * x + r[1] * y + r[2] * z + tx);
        target[at + index + 1] = Math.fround(r[3] * x + r[4] * y + r[5] * z + ty);
        target[at + index + 2] = Math.fround(r[6] * x + r[7] * y + r[8] * z + tz);
    }
    return at + source.length;
}
