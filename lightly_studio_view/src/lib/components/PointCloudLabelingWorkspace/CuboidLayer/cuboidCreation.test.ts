import { describe, expect, it } from 'vitest';
import { clampToBounds, computePointsThreshold } from './cuboidCreation';
import type { Bounds3 } from '$lib/components/PointCloudLabelingWorkspace/domain';

const BOUNDS: Bounds3 = { min: [-10, -5, 0], max: [10, 5, 3] };

describe('computePointsThreshold', () => {
    it('returns zero when element has no height', () => {
        expect(computePointsThreshold(60, 0, 20)).toBe(0);
    });

    it('returns zero when depth is zero', () => {
        expect(computePointsThreshold(60, 600, 0)).toBe(0);
    });

    it('returns zero when depth is negative', () => {
        expect(computePointsThreshold(60, 600, -5)).toBe(0);
    });

    it('scales linearly with depth', () => {
        const t1 = computePointsThreshold(60, 600, 10);
        const t2 = computePointsThreshold(60, 600, 20);
        expect(t2).toBeCloseTo(t1 * 2, 5);
    });

    it('scales linearly with pick radius', () => {
        const t1 = computePointsThreshold(60, 600, 20, 4);
        const t2 = computePointsThreshold(60, 600, 20, 8);
        expect(t2).toBeCloseTo(t1 * 2, 5);
    });

    it('produces a physically reasonable threshold', () => {
        // fov=60°, 600px height, 20m depth, 4px radius
        // visibleWorldHeight = 2 * 20 * tan(30°) ≈ 23.09 m
        // threshold = 23.09 / 600 * 4 ≈ 0.154 m
        const t = computePointsThreshold(60, 600, 20, 4);
        expect(t).toBeCloseTo(0.154, 2);
    });

    it('uses the default 4px pick radius', () => {
        const withDefault = computePointsThreshold(60, 600, 20);
        const withExplicit = computePointsThreshold(60, 600, 20, 4);
        expect(withDefault).toBeCloseTo(withExplicit, 10);
    });
});

describe('clampToBounds', () => {
    it('passes through a position already within bounds', () => {
        expect(clampToBounds([0, 0, 1], BOUNDS)).toEqual([0, 0, 1]);
    });

    it('clamps a position below each axis minimum', () => {
        expect(clampToBounds([-20, -10, -1], BOUNDS)).toEqual([-10, -5, 0]);
    });

    it('clamps a position above each axis maximum', () => {
        expect(clampToBounds([20, 10, 5], BOUNDS)).toEqual([10, 5, 3]);
    });

    it('clamps independently per axis', () => {
        expect(clampToBounds([0, -10, 5], BOUNDS)).toEqual([0, -5, 3]);
    });

    it('leaves a position exactly on the boundary unchanged', () => {
        expect(clampToBounds([-10, -5, 0], BOUNDS)).toEqual([-10, -5, 0]);
        expect(clampToBounds([10, 5, 3], BOUNDS)).toEqual([10, 5, 3]);
    });
});
