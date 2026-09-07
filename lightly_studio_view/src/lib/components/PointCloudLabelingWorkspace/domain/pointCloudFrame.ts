import type { Bounds3, PackedPointAttribute, PointCloudFrame } from './contracts';
import { assertCompatibleCoordinates, canonicalCoordinateFrame, freezeVector } from './coordinates';
import { validateCamera, validateFrameSource, validateTimestamp } from './frameMetadata';

interface PointCloudFrameInput extends Omit<
    PointCloudFrame,
    'positions' | 'intensity' | 'color' | 'bounds'
> {
    readonly positions: Float32Array;
    readonly intensity?: Float32Array;
    readonly color?: Float32Array;
}

function pack(values: Float32Array, length: number, normalized = false): PackedPointAttribute {
    if (values.length !== length || !values.every(Number.isFinite)) {
        throw new Error('Packed point attributes must have matching lengths and finite values.');
    }
    if (normalized && values.some((value) => value < 0 || value > 1)) {
        throw new Error('Intensity and color must be normalized to [0, 1].');
    }
    const owned = new Float32Array(values);
    return Object.freeze({ length, copy: () => new Float32Array(owned) });
}

function computeBounds(positions: Float32Array): Bounds3 | null {
    if (positions.length === 0) return null;
    const min: [number, number, number] = [Infinity, Infinity, Infinity];
    const max: [number, number, number] = [-Infinity, -Infinity, -Infinity];
    for (let i = 0; i < positions.length; i++) {
        const axis = i % 3;
        min[axis] = Math.min(min[axis], positions[i]);
        max[axis] = Math.max(max[axis], positions[i]);
    }
    return Object.freeze({ min: freezeVector(min), max: freezeVector(max) });
}

function freezeMetadata<T extends object>(value: T): T {
    Object.values(value).forEach((child) => {
        if (child !== null && typeof child === 'object') freezeMetadata(child);
    });
    return Object.freeze(value);
}

function validateFrameInput(input: PointCloudFrameInput): void {
    assertCompatibleCoordinates(
        input.coordinateFrame,
        canonicalCoordinateFrame(input.coordinateFrame.id)
    );
    if (input.positions.length % 3 !== 0) {
        throw new Error('Positions must contain xyz triples.');
    }
    validateTimestamp(input.timestamp);
    validateFrameSource(input.source);
    if (
        !Number.isSafeInteger(input.sourcePointCount) ||
        input.sourcePointCount < input.positions.length / 3
    ) {
        throw new Error(
            'Source point count must be an integer at least as large as the displayed count.'
        );
    }
    input.cameras.forEach((camera) => validateCamera(camera, input.coordinateFrame.id));
}

function cloneFrameMetadata(input: PointCloudFrameInput): object {
    return freezeMetadata(
        structuredClone({
            id: input.id,
            source: input.source,
            sourcePointCount: input.sourcePointCount,
            timestamp: input.timestamp,
            coordinateFrame: input.coordinateFrame,
            cameras: input.cameras
        })
    );
}

/** Copies, validates, bounds, and freezes provider output for shared domain consumption. */
export function createPointCloudFrame(input: PointCloudFrameInput): PointCloudFrame {
    validateFrameInput(input);
    return Object.freeze({
        ...cloneFrameMetadata(input),
        positions: pack(input.positions, input.positions.length),
        intensity: input.intensity && pack(input.intensity, input.positions.length / 3, true),
        color: input.color && pack(input.color, input.positions.length, true),
        bounds: computeBounds(input.positions)
    });
}
