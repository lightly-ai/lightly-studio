import { describe, expect, it } from 'vitest';
import type { Bounds3 } from '$lib/components/PointCloudLabelingWorkspace/domain';
import { computeGroundPlaneLayout } from './groundPlaneLayout';

describe('computeGroundPlaneLayout', () => {
    it('centers the grid under the bounds and fades near the cloud edges', () => {
        const bounds: Bounds3 = { min: [-60, -4, 1], max: [60, 4, 5] };

        const layout = computeGroundPlaneLayout(bounds);

        expect(layout).not.toBeNull();
        expect(layout?.fadeDistance).toBeCloseTo(Math.hypot(120, 8) * 0.65);
        expect(layout?.center[0]).toBeCloseTo(0);
        expect(layout?.center[1]).toBeCloseTo(0);
        expect(layout?.center[2]).toBeLessThan(1);
    });

    it('scales the fade distance for small footprints', () => {
        const bounds: Bounds3 = { min: [-1, -1, 0], max: [1, 1, 1] };

        expect(computeGroundPlaneLayout(bounds)?.fadeDistance).toBeCloseTo(Math.hypot(2, 2) * 0.65);
    });

    it('returns null for an empty footprint', () => {
        const bounds: Bounds3 = { min: [0, 0, 0], max: [0, 0, 0] };

        expect(computeGroundPlaneLayout(bounds)).toBeNull();
    });
});
