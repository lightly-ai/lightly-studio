import { describe, expect, it } from 'vitest';
import {
    composeTransforms,
    IDENTITY_TRANSFORM,
    invertTransform,
    rigidTransform,
    transformPositionsInto
} from './rigidTransform';

/** A quarter turn about z, the yaw that mounts a sensor facing left. */
const QUARTER_TURN = Math.SQRT1_2;

describe('rigidTransform', () => {
    it('turns a quaternion into the rotation it describes', () => {
        const transform = rigidTransform([0, 0, 0], [0, 0, QUARTER_TURN, QUARTER_TURN])!;

        expect([...transform.rotation].map((value) => Math.round(value))).toEqual([
            0, -1, 0, 1, 0, 0, 0, 0, 1
        ]);
    });

    it('normalizes a quaternion that is not quite unit length', () => {
        const scaled = rigidTransform([0, 0, 0], [0, 0, QUARTER_TURN * 3, QUARTER_TURN * 3])!;

        scaled.rotation.forEach((value, index) => {
            expect(value).toBeCloseTo([0, -1, 0, 1, 0, 0, 0, 0, 1][index], 6);
        });
    });

    it('refuses a rotation it cannot describe rather than guessing one', () => {
        expect(rigidTransform([0, 0, 0], [0, 0, 0, 0])).toBeNull();
        expect(rigidTransform([Number.NaN, 0, 0], [0, 0, 0, 1])).toBeNull();
        expect(rigidTransform([0, 0, 0], [0, 0, Number.POSITIVE_INFINITY, 1])).toBeNull();
    });
});

describe('composeTransforms', () => {
    it('applies the inner transform first', () => {
        const yaw = rigidTransform([0, 0, 0], [0, 0, QUARTER_TURN, QUARTER_TURN])!;
        const shift = rigidTransform([1, 0, 0], [0, 0, 0, 1])!;

        // Rotating after shifting sends the shift along +x onto +y.
        const composed = composeTransforms(yaw, shift);

        expect(composed.translation[0]).toBeCloseTo(0, 6);
        expect(composed.translation[1]).toBeCloseTo(1, 6);
    });

    it('leaves a transform unchanged when composed with the identity', () => {
        const transform = rigidTransform([2, -3, 1], [0, 0, QUARTER_TURN, QUARTER_TURN])!;

        const composed = composeTransforms(IDENTITY_TRANSFORM, transform);

        expect([...composed.rotation, ...composed.translation]).toEqual([
            ...transform.rotation,
            ...transform.translation
        ]);
    });
});

describe('invertTransform', () => {
    it('undoes the transform it inverts', () => {
        const transform = rigidTransform([2, -3, 1], [0, 0, QUARTER_TURN, QUARTER_TURN])!;

        const roundTrip = composeTransforms(transform, invertTransform(transform));

        roundTrip.rotation.forEach((value, index) => {
            expect(value).toBeCloseTo(IDENTITY_TRANSFORM.rotation[index], 6);
        });
        roundTrip.translation.forEach((value) => expect(value).toBeCloseTo(0, 6));
    });
});

describe('transformPositionsInto', () => {
    it('writes the transformed points at the offset and reports the next one', () => {
        const target = new Float32Array(9);
        const yaw = rigidTransform([0, 0, 5], [0, 0, QUARTER_TURN, QUARTER_TURN])!;

        const next = transformPositionsInto(target, 3, new Float32Array([1, 0, 0, 0, 2, 0]), yaw);

        expect(next).toBe(9);
        expect([...target].map((value) => Math.round(value))).toEqual([0, 0, 0, 0, 1, 5, -2, 0, 5]);
    });
});
