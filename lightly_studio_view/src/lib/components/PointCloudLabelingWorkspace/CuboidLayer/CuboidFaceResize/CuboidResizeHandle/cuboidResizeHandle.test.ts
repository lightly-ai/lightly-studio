import { describe, expect, it } from 'vitest';
import { computeHandleScale, HANDLE_SIZE, PERP_SCALE_INDICES } from './cuboidResizeHandle';

describe('PERP_SCALE_INDICES', () => {
    it('maps axisIndex 0 to parent Z (2) and Y (1)', () => {
        expect(PERP_SCALE_INDICES[0]).toEqual([2, 1]);
    });

    it('maps axisIndex 1 to parent X (0) and Z (2)', () => {
        expect(PERP_SCALE_INDICES[1]).toEqual([0, 2]);
    });

    it('maps axisIndex 2 to parent X (0) and Y (1)', () => {
        expect(PERP_SCALE_INDICES[2]).toEqual([0, 1]);
    });
});

describe('computeHandleScale', () => {
    // fov=60°, tan(30°) ≈ 0.57735
    // cameraDistance=10: eyeDistance = min(10 * 0.57735, 7) = 5.7735, base = 5.7735 * 0.5 = 2.8868
    const base = 10 * Math.tan((Math.PI / 180) * 30) * HANDLE_SIZE;

    it('returns uniform scale with unit parent scale', () => {
        const [sx, sy, sz] = computeHandleScale({
            cameraDistance: 10,
            fov: 60,
            parentScale: [1, 1, 1],
            axisIndex: 0
        });
        expect(sx).toBeCloseTo(base);
        expect(sy).toBeCloseTo(base);
        expect(sz).toBeCloseTo(base);
    });

    it('caps eyeDistance at 7 when camera is very far away', () => {
        // cameraDistance=100, fov=60: 100 * tan(30°) ≈ 57.7 > 7, so eyeDistance=7
        const cappedBase = 7 * HANDLE_SIZE;
        const [sx, sy, sz] = computeHandleScale({
            cameraDistance: 100,
            fov: 60,
            parentScale: [1, 1, 1],
            axisIndex: 0
        });
        expect(sx).toBeCloseTo(cappedBase);
        expect(sy).toBeCloseTo(cappedBase);
        expect(sz).toBeCloseTo(cappedBase);
    });

    it('compensates sz for parent scale along the face axis', () => {
        // axisIndex=0, parentScale[0]=2 → sz = base / 2
        const [, , sz] = computeHandleScale({
            cameraDistance: 10,
            fov: 60,
            parentScale: [2, 1, 1],
            axisIndex: 0
        });
        expect(sz).toBeCloseTo(base / 2);
    });

    it('compensates sx and sy for perpendicular parent scale (axisIndex=0)', () => {
        // axisIndex=0: xIdx=2 (parentZ), yIdx=1 (parentY)
        // parentScale=[1, 3, 4] → sx=base/4, sy=base/3
        const [sx, sy] = computeHandleScale({
            cameraDistance: 10,
            fov: 60,
            parentScale: [1, 3, 4],
            axisIndex: 0
        });
        expect(sx).toBeCloseTo(base / 4);
        expect(sy).toBeCloseTo(base / 3);
    });

    it('compensates sx and sy for perpendicular parent scale (axisIndex=1)', () => {
        // axisIndex=1: xIdx=0 (parentX), yIdx=2 (parentZ)
        // parentScale=[2, 1, 5] → sx=base/2, sy=base/5
        const base1 = 10 * Math.tan((Math.PI / 180) * 30) * HANDLE_SIZE;
        const [sx, sy] = computeHandleScale({
            cameraDistance: 10,
            fov: 60,
            parentScale: [2, 1, 5],
            axisIndex: 1
        });
        expect(sx).toBeCloseTo(base1 / 2);
        expect(sy).toBeCloseTo(base1 / 5);
    });

    it('compensates sx and sy for perpendicular parent scale (axisIndex=2)', () => {
        // axisIndex=2: xIdx=0 (parentX), yIdx=1 (parentY)
        // parentScale=[3, 6, 1] → sx=base/3, sy=base/6
        const [sx, sy] = computeHandleScale({
            cameraDistance: 10,
            fov: 60,
            parentScale: [3, 6, 1],
            axisIndex: 2
        });
        expect(sx).toBeCloseTo(base / 3);
        expect(sy).toBeCloseTo(base / 6);
    });

    it('falls back to divisor 1 when a parent scale component is zero', () => {
        const [sx, sy, sz] = computeHandleScale({
            cameraDistance: 10,
            fov: 60,
            parentScale: [0, 0, 0],
            axisIndex: 0
        });
        expect(sx).toBeCloseTo(base);
        expect(sy).toBeCloseTo(base);
        expect(sz).toBeCloseTo(base);
    });

    it('falls back to divisor 1 when a parent scale component is negative', () => {
        const [, , sz] = computeHandleScale({
            cameraDistance: 10,
            fov: 60,
            parentScale: [-2, 1, 1],
            axisIndex: 0
        });
        expect(sz).toBeCloseTo(base);
    });
});
