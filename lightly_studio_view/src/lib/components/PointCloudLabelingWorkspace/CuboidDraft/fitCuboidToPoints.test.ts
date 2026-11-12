import { describe, expect, it } from 'vitest';
import type { PointBatch } from '$lib/components/PointCloudViewer';
import { getDraftRectangle } from './cuboidDraft';
import { fitMissingAxis } from './fitCuboidToPoints';

const batch = (points: number[], count = points.length / 3): PointBatch => ({
    positions: new Float32Array(points),
    intensities: new Float32Array(count),
    count
});
const top = getDraftRectangle('top', [0, 0, -1], [4, 2, -1]);

describe('fitMissingAxis', () => {
    it('fits Z to the points inside a top-view rectangle', () => {
        const points = [1, 1, 0.25, 3, 1, 1.75, 9, 9, 50]; // last point is outside
        expect(fitMissingAxis(top, batch(points))).toEqual({ min: 0.25, max: 1.75 });
    });
    it('counts points on the rectangle border as inside', () => {
        expect(fitMissingAxis(top, batch([0, 0, 0.5, 4, 2, 1.5]))).toEqual({ min: 0.5, max: 1.5 });
    });
    it('fits X in the side view', () => {
        const side = getDraftRectangle('side', [5, 0, 0], [5, 4, 2]);
        expect(fitMissingAxis(side, batch([1, 1, 1, 3, 2, 1]))).toEqual({ min: 1, max: 3 });
    });
    it('fits Y in the front view', () => {
        const front = getDraftRectangle('front', [0, 5, 0], [4, 5, 2]);
        expect(fitMissingAxis(front, batch([1, -2, 1, 2, 6, 1]))).toEqual({ min: -2, max: 6 });
    });
    it('ignores points beyond count', () => {
        expect(fitMissingAxis(top, batch([1, 1, 0.5, 1, 1, 99], 1))).toEqual({
            min: 0.5,
            max: 0.5
        });
    });
    it('reads every accumulated segment', () => {
        const merged = { ...batch([]), segments: [batch([1, 1, 0.25]), batch([2, 1, 1.5])] };
        expect(fitMissingAxis(top, merged)).toEqual({ min: 0.25, max: 1.5 });
    });
    it('rests on the plane with the shorter side as height when no point is inside', () => {
        expect(fitMissingAxis(top, batch([9, 9, 9]))).toEqual({ min: -1, max: 1 });
    });
    it('centres on the plane in side and front views when no point is inside', () => {
        const side = getDraftRectangle('side', [5, 0, 0], [5, 4, 2]);
        expect(fitMissingAxis(side, undefined)).toEqual({ min: 4, max: 6 });
    });
});
