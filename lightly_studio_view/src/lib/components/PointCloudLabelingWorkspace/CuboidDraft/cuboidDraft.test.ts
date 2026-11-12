import { describe, expect, it } from 'vitest';
import {
    getDefaultCuboidBox,
    getDraftBox,
    getDraftRectangle,
    getHeightExtent,
    getMissingAxis,
    isDrag
} from './cuboidDraft';

describe('isDrag', () => {
    it('treats a move under 4 px as a click', () => {
        expect(isDrag({ x: 10, y: 10 }, { x: 12, y: 13 })).toBe(false); // 3.6 px
    });
    it('treats a move of 4 px or more as a drag', () => {
        expect(isDrag({ x: 10, y: 10 }, { x: 14, y: 10 })).toBe(true);
    });
});

describe('getMissingAxis', () => {
    it.each([
        ['top', 2],
        ['perspective', 2],
        ['side', 0],
        ['front', 1]
    ] as const)('%s misses axis %i', (mode, axis) => expect(getMissingAxis(mode)).toBe(axis));
});

describe('getDraftRectangle', () => {
    it('spans the two corners in the top view', () => {
        expect(getDraftRectangle('top', [1, 2, -0.5], [5, 4, -0.5])).toEqual({
            missingAxis: 2,
            planeCoordinate: -0.5,
            min: [1, 2, -0.5],
            max: [5, 4, -0.5]
        });
    });
    it('gives the same rectangle for a reversed drag', () => {
        expect(getDraftRectangle('top', [5, 4, -0.5], [1, 2, -0.5])).toEqual(
            getDraftRectangle('top', [1, 2, -0.5], [5, 4, -0.5])
        );
    });
    it('uses Y and Z in the side view', () => {
        const r = getDraftRectangle('side', [7, 0, 0], [7, 4, 2]);
        expect(r).toMatchObject({
            missingAxis: 0,
            planeCoordinate: 7,
            min: [7, 0, 0],
            max: [7, 4, 2]
        });
    });
    it('uses X and Z in the front view', () => {
        const r = getDraftRectangle('front', [0, 3, 0], [4, 3, 2]);
        expect(r).toMatchObject({ missingAxis: 1, planeCoordinate: 3 });
    });
});

describe('getDraftBox', () => {
    const rectangle = getDraftRectangle('top', [1, 2, 0], [5, 4, 0]);
    it('returns a flat preview box without an extent', () => {
        expect(getDraftBox(rectangle)).toEqual({ center: [3, 3, 0], size: [4, 2, 0.1] });
    });
    it('spans the extent on the missing axis', () => {
        expect(getDraftBox(rectangle, { min: 0, max: 1.5 })).toEqual({
            center: [3, 3, 0.75],
            size: [4, 2, 1.5]
        });
    });
    it('clamps a near-zero side to 0.1 without moving the centre', () => {
        const thin = getDraftRectangle('top', [1, 2, 0], [1.01, 4, 0]);
        const box = getDraftBox(thin, { min: 0, max: 1 });
        expect(box.size[0]).toBe(0.1);
        expect(box.center[0]).toBeCloseTo(1.005);
    });
});

describe('getHeightExtent', () => {
    it('raises the footprint from its plane to the pointer height', () => {
        const r = getDraftRectangle('perspective', [0, 0, -1], [4, 2, -1]);
        expect(getHeightExtent(r, 1.5)).toEqual({ min: -1, max: 1.5 });
    });
    it('keeps the 0.1 minimum when the pointer is below the plane', () => {
        const r = getDraftRectangle('perspective', [0, 0, -1], [4, 2, -1]);
        expect(getHeightExtent(r, -3)).toEqual({ min: -1, max: -0.9 });
    });
});

describe('getDefaultCuboidBox', () => {
    it('returns a cube of 2% of the diagonal resting on the position', () => {
        const bounds = { min: [0, 0, 0], max: [30, 40, 0] } as const; // diagonal 50
        expect(getDefaultCuboidBox([2, 3, 0], bounds)).toEqual({
            center: [2, 3, 0.5],
            size: [1, 1, 1]
        });
    });
    it('uses the 0.1 minimum for empty bounds', () => {
        const bounds = { min: [0, 0, 0], max: [0, 0, 0] } as const;
        expect(getDefaultCuboidBox([0, 0, 0], bounds).size).toEqual([0.1, 0.1, 0.1]);
    });
});
