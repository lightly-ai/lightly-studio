import { describe, expect, it } from 'vitest';
import { computeFaceNormalWorld, computeResizedCuboid, MIN_CUBOID_SIZE } from './cuboidFaceResize';

describe('computeFaceNormalWorld', () => {
    it('returns the local normal unchanged for identity rotation', () => {
        const identity = [0, 0, 0, 1] as const;
        expect(computeFaceNormalWorld({ axis: 0, sign: 1, rotation: identity })).toBeCloseToTuple([
            1, 0, 0
        ]);
        expect(computeFaceNormalWorld({ axis: 0, sign: -1, rotation: identity })).toBeCloseToTuple([
            -1, 0, 0
        ]);
        expect(computeFaceNormalWorld({ axis: 1, sign: 1, rotation: identity })).toBeCloseToTuple([
            0, 1, 0
        ]);
        expect(computeFaceNormalWorld({ axis: 1, sign: -1, rotation: identity })).toBeCloseToTuple([
            0, -1, 0
        ]);
        expect(computeFaceNormalWorld({ axis: 2, sign: 1, rotation: identity })).toBeCloseToTuple([
            0, 0, 1
        ]);
        expect(computeFaceNormalWorld({ axis: 2, sign: -1, rotation: identity })).toBeCloseToTuple([
            0, 0, -1
        ]);
    });

    it('rotates the +X normal to +Y after a 90° rotation around Z', () => {
        // 90° around Z: q = [0, 0, sin(45°), cos(45°)]
        const s = Math.SQRT1_2;
        const q = [0, 0, s, s] as const;
        expect(computeFaceNormalWorld({ axis: 0, sign: 1, rotation: q })).toBeCloseToTuple([
            0, 1, 0
        ]);
    });

    it('rotates the +Y normal to +Z after a 90° rotation around X', () => {
        // 90° around X: q = [sin(45°), 0, 0, cos(45°)]
        const s = Math.SQRT1_2;
        const q = [s, 0, 0, s] as const;
        expect(computeFaceNormalWorld({ axis: 1, sign: 1, rotation: q })).toBeCloseToTuple([
            0, 0, 1
        ]);
    });

    it('returns a unit vector for an arbitrary rotation', () => {
        const q = [0.5, 0.5, 0.5, 0.5] as const;
        const result = computeFaceNormalWorld({ axis: 0, sign: 1, rotation: q });
        const magnitude = Math.sqrt(result[0] ** 2 + result[1] ** 2 + result[2] ** 2);
        expect(magnitude).toBeCloseTo(1);
    });
});

describe('computeResizedCuboid', () => {
    const defaultParams = {
        originalCenter: [0, 0, 0] as const,
        originalSize: [4, 2, 6] as const,
        axis: 0 as 0 | 1 | 2,
        faceNormalWorld: [1, 0, 0] as const,
        delta: 0
    };

    it('expands the +X face: size grows along x, center shifts right', () => {
        const result = computeResizedCuboid({ ...defaultParams, delta: 2 });
        expect(result.size).toEqual([6, 2, 6]);
        expect(result.center).toBeCloseToTuple([1, 0, 0]);
        expect(result.center[0] + result.size[0] / 2).toBeCloseTo(4);
        expect(result.center[0] - result.size[0] / 2).toBeCloseTo(-2);
    });

    it('shrinks the +Y face: size shrinks along y, center shifts down', () => {
        const result = computeResizedCuboid({
            ...defaultParams,
            axis: 1,
            faceNormalWorld: [0, 1, 0] as const,
            delta: -1
        });
        expect(result.size).toEqual([4, 1, 6]);
        expect(result.center).toBeCloseToTuple([0, -0.5, 0]);
    });

    it('expands the +Z face: center shifts up', () => {
        const result = computeResizedCuboid({
            ...defaultParams,
            axis: 2,
            faceNormalWorld: [0, 0, 1] as const,
            delta: 4
        });
        expect(result.size).toEqual([4, 2, 10]);
        expect(result.center).toBeCloseToTuple([0, 0, 2]);
    });

    it('keeps the opposite face fixed when expanding', () => {
        // +X face at x = center.x + size.x/2 = 2.
        // After expanding by 2, +X face should move to 2+2=4.
        // -X face should stay at center.x - size.x/2 = -2.
        const result = computeResizedCuboid({ ...defaultParams, delta: 2 });
        const newPlusFace = result.center[0] + result.size[0] / 2;
        const newMinusFace = result.center[0] - result.size[0] / 2;
        expect(newPlusFace).toBeCloseTo(4);
        expect(newMinusFace).toBeCloseTo(-2);
    });

    it('clamps size to MIN_CUBOID_SIZE and stops center from over-shifting', () => {
        const result = computeResizedCuboid({ ...defaultParams, delta: -100 });
        expect(result.size[0]).toBe(MIN_CUBOID_SIZE);
        // center shifts only by half the actual (clamped) delta
        const actualDelta = MIN_CUBOID_SIZE - defaultParams.originalSize[0];
        expect(result.center[0]).toBeCloseTo(actualDelta / 2);
    });

    it('returns original values when delta is zero', () => {
        const result = computeResizedCuboid({
            ...defaultParams,
            axis: 1,
            faceNormalWorld: [0, 1, 0] as const
        });
        expect(result.center).toEqual([0, 0, 0]);
        expect(result.size).toEqual([4, 2, 6]);
    });

    it('works for the -X face (negative normal direction)', () => {
        // Dragging -X face outward (positive delta along -X normal means moving in -X direction).
        const result = computeResizedCuboid({
            ...defaultParams,
            faceNormalWorld: [-1, 0, 0] as const,
            delta: 2
        });
        expect(result.size[0]).toBeCloseTo(6);
        // Center shifts toward -X by 1
        expect(result.center[0]).toBeCloseTo(-1);
        // +X face stays fixed at 2
        expect(result.center[0] + result.size[0] / 2).toBeCloseTo(2);
    });
});

// Custom matcher for approximate tuple equality
expect.extend({
    toBeCloseToTuple(received: readonly number[], expected: readonly number[]) {
        const eps = 1e-6;
        const pass = received.every((v, i) => Math.abs(v - expected[i]) < eps);
        return {
            pass,
            message: () =>
                `expected ${JSON.stringify(received)} to be close to ${JSON.stringify(expected)}`
        };
    }
});

declare module 'vitest' {
    interface Assertion {
        toBeCloseToTuple(expected: readonly number[]): void;
    }
}
