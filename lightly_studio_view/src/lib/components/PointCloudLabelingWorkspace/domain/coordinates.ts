import type { CoordinateFrame, CuboidAnnotation, Quaternion, Vector3 } from './contracts';

/** Creates the canonical metre/right-handed frame descriptor for an identifier. */
export const canonicalCoordinateFrame = (id: string): CoordinateFrame =>
    Object.freeze({ id, convention: 'right-handed-x-forward-y-left-z-up', unit: 'metre' });

/**
 * Ensures two geometries can be combined without an implicit conversion.
 * @throws If frame identity, convention, or unit differs.
 */
export function assertCompatibleCoordinates(actual: CoordinateFrame, expected: CoordinateFrame) {
    if (
        actual.id !== expected.id ||
        actual.unit !== expected.unit ||
        actual.convention !== expected.convention
    ) {
        throw new Error('Coordinate frames differ; an explicit rigid transform is required.');
    }
}

/** Validates and freezes a vector so shared geometry cannot be mutated. */
export function freezeVector(value: Vector3): Vector3 {
    const values = Array.from(value);
    if (values.length !== 3 || !values.every(Number.isFinite)) {
        throw new Error('A vector must contain three finite coordinates.');
    }
    return Object.freeze(values) as Vector3;
}

/** Validates and freezes a unit quaternion in xyzw order. */
export function freezeRotation(value: Quaternion): Quaternion {
    const values = Array.from(value);
    if (
        values.length !== 4 ||
        !values.every(Number.isFinite) ||
        Math.abs(Math.hypot(...values) - 1) > 1e-6
    ) {
        throw new Error('Rotation must be a unit quaternion in xyzw order.');
    }
    return Object.freeze(values) as Quaternion;
}

/** Validates and returns an immutable annotation suitable for persistence or rendering. */
export function createCuboidAnnotation(input: CuboidAnnotation): CuboidAnnotation {
    assertCompatibleCoordinates(
        input.coordinateFrame,
        canonicalCoordinateFrame(input.coordinateFrame.id)
    );
    const size = freezeVector(input.size);
    if (size.some((extent) => extent <= 0)) throw new Error('Cuboid extents must be positive.');
    if (input.keyframeId !== null && input.trackId === null) {
        throw new Error('A keyframe annotation must belong to a track.');
    }
    return Object.freeze({
        ...input,
        coordinateFrame: canonicalCoordinateFrame(input.coordinateFrame.id),
        center: freezeVector(input.center),
        size,
        rotation: freezeRotation(input.rotation)
    });
}
