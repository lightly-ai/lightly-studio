import { describe, expect, it } from 'vitest';
import { Vector3 } from 'three';
import {
    applyResizeDelta,
    getFaceAxis,
    getWorldFaceCenter,
    getWorldFaceNormal
} from './cuboidResize';
import type { CuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/domain';

const IDENTITY: [number, number, number, number] = [0, 0, 0, 1];
const YAW_90: [number, number, number, number] = [0, 0, Math.sin(Math.PI / 4), Math.cos(Math.PI / 4)];

/** Cuboid centred at origin, 4 × 2 × 2 m, no rotation. */
const BASE: CuboidAnnotation = {
    id: 'a',
    frameId: 'f',
    coordinateFrame: { id: 'c', convention: 'right-handed-x-forward-y-left-z-up', unit: 'meter' },
    annotationClassId: 'cls',
    annotationSourceId: 'src',
    trackId: null,
    keyframeId: null,
    center: [0, 0, 0],
    size: [4, 2, 2],
    rotation: IDENTITY
};

describe('getFaceAxis', () => {
    it.each([
        ['max-x', 0, 1],
        ['min-x', 0, -1],
        ['max-y', 1, 1],
        ['min-y', 1, -1],
        ['max-z', 2, 1],
        ['min-z', 2, -1]
    ] as const)('%s → axis %i sign %i', (handle, axis, sign) => {
        expect(getFaceAxis(handle)).toEqual({ axis, sign });
    });
});

describe('getWorldFaceNormal', () => {
    it('returns local axis direction for identity rotation', () => {
        const n = getWorldFaceNormal('max-x', IDENTITY);
        expect(n.x).toBeCloseTo(1);
        expect(n.y).toBeCloseTo(0);
        expect(n.z).toBeCloseTo(0);
    });

    it('rotates face normal with 90° yaw', () => {
        // 90° yaw (z-rotation): local +x maps to world +y (left in this frame)
        const n = getWorldFaceNormal('max-x', YAW_90);
        expect(n.x).toBeCloseTo(0);
        expect(n.y).toBeCloseTo(1);
        expect(n.z).toBeCloseTo(0);
    });

    it('min-z normal points in -z for identity rotation', () => {
        const n = getWorldFaceNormal('min-z', IDENTITY);
        expect(n.x).toBeCloseTo(0);
        expect(n.y).toBeCloseTo(0);
        expect(n.z).toBeCloseTo(-1);
    });
});

describe('getWorldFaceCenter', () => {
    it('places max-x face at +x half-extent from center', () => {
        const c = getWorldFaceCenter('max-x', BASE);
        expect(c).toEqual(new Vector3(2, 0, 0));
    });

    it('places min-y face at -y half-extent from center', () => {
        const c = getWorldFaceCenter('min-y', BASE);
        expect(c).toEqual(new Vector3(0, -1, 0));
    });

    it('accounts for cuboid center offset', () => {
        const shifted = { ...BASE, center: [10, 5, 2] as [number, number, number] };
        const c = getWorldFaceCenter('max-z', shifted);
        expect(c.x).toBeCloseTo(10);
        expect(c.y).toBeCloseTo(5);
        expect(c.z).toBeCloseTo(3); // 2 + (2/2)
    });
});

describe('applyResizeDelta', () => {
    it('increases size along max-x and shifts center to keep min-x face fixed', () => {
        const result = applyResizeDelta(BASE, 'max-x', 1);
        expect(result.size[0]).toBeCloseTo(5);
        expect(result.size[1]).toBeCloseTo(2);
        expect(result.size[2]).toBeCloseTo(2);
        // min-x face was at x = -2; after resize it stays at x = -2
        // new center = -2 + 5/2 = 0.5
        expect(result.center[0]).toBeCloseTo(0.5);
        expect(result.center[1]).toBeCloseTo(0);
        expect(result.center[2]).toBeCloseTo(0);
    });

    it('decreases size along min-x and shifts center to keep max-x face fixed', () => {
        // delta > 0 means move the min-x face outward (in -x direction), enlarging
        // negative delta shrinks from the min-x side
        const result = applyResizeDelta(BASE, 'min-x', -1);
        expect(result.size[0]).toBeCloseTo(3);
        // max-x face was at x = +2; stays at +2; new center = 2 - 3/2 = 0.5
        expect(result.center[0]).toBeCloseTo(0.5);
    });

    it('enforces minimum 1e-6 m size', () => {
        const result = applyResizeDelta(BASE, 'max-x', -100);
        expect(result.size[0]).toBeCloseTo(1e-6);
    });

    it('clamps center correctly at minimum size', () => {
        // Shrink max-x to minimum; opposite face (min-x) stays at x = -2
        // new center = -2 + 1e-6/2 ≈ -2
        const result = applyResizeDelta(BASE, 'max-x', -100);
        expect(result.center[0]).toBeCloseTo(-2);
    });

    it('resizes along y axis correctly', () => {
        const result = applyResizeDelta(BASE, 'max-y', 2);
        expect(result.size[1]).toBeCloseTo(4);
        // min-y was at y = -1; stays at -1; new center = -1 + 4/2 = 1
        expect(result.center[1]).toBeCloseTo(1);
    });

    it('resizes along z axis correctly', () => {
        const result = applyResizeDelta(BASE, 'min-z', 1);
        expect(result.size[2]).toBeCloseTo(3);
        // max-z face was at z = +1; stays; new center = 1 - 3/2 = -0.5
        expect(result.center[2]).toBeCloseTo(-0.5);
    });

    it('keeps size and other axes unchanged', () => {
        const result = applyResizeDelta(BASE, 'max-x', 1);
        expect(result.id).toBe(BASE.id);
        expect(result.rotation).toBe(BASE.rotation);
        expect(result.size[1]).toBe(BASE.size[1]);
        expect(result.size[2]).toBe(BASE.size[2]);
    });

    it('treats negative size as magnitude and preserves sign', () => {
        const negative = { ...BASE, size: [-4, 2, 2] as [number, number, number] };
        const result = applyResizeDelta(negative, 'max-x', 1);
        expect(result.size[0]).toBeCloseTo(-5);
    });

    it('keeps opposite face fixed when size is negative', () => {
        // size[0] = -4 → magnitude 4 → max-x face at x = +2, min-x face at x = -2
        const negative = { ...BASE, size: [-4, 2, 2] as [number, number, number] };
        const result = applyResizeDelta(negative, 'max-x', 1);
        // min-x face stays at x = -2; new center = -2 + 5/2 = 0.5
        expect(result.center[0]).toBeCloseTo(0.5);
    });

    it('clamps negative size to negative minimum', () => {
        const negative = { ...BASE, size: [-4, 2, 2] as [number, number, number] };
        const result = applyResizeDelta(negative, 'max-x', -100);
        expect(result.size[0]).toBeCloseTo(-1e-6);
    });

    it('handles rotated cuboids by keeping opposite face in world space', () => {
        const rotated = { ...BASE, rotation: YAW_90 };
        // max-x face normal is in world +y direction after 90° yaw
        // center at origin, size[0] = 4 → max-x face at world y = +2
        const result = applyResizeDelta(rotated, 'max-x', 1);
        expect(result.size[0]).toBeCloseTo(5);
        // min-x face (world -y, at y=-2) stays fixed
        // new center = world(-2*y) + worldNormal(+y) * 5/2 = (0, -2 + 2.5, 0) = (0, 0.5, 0)
        expect(result.center[0]).toBeCloseTo(0);
        expect(result.center[1]).toBeCloseTo(0.5);
        expect(result.center[2]).toBeCloseTo(0);
    });
});
