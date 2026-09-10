import { describe, expect, it } from 'vitest';
import { createAnnotationFixture } from '$lib/components/PointCloudLabelingWorkspace/domain';
import { createCuboidTooltip } from './cuboidTooltip';

describe('createCuboidTooltip', () => {
    it('formats cuboid details using the specified display precision', () => {
        const tooltip = createCuboidTooltip({
            annotation: {
                ...createAnnotationFixture(),
                center: [10, -2, 1.234],
                size: [4.5, 1.8, 1.5],
                rotation: [0, 0, Math.sin(Math.PI / 8), Math.cos(Math.PI / 8)]
            },
            annotationClassName: 'Vehicle'
        });

        expect(tooltip).toEqual({
            annotationClassName: 'Vehicle',
            location: 'X: 10.00  Y: -2.00  Z: 1.23',
            dimensions: '4.50 × 1.80 × 1.50 m',
            rotation: '45.0°',
            annotationSourceId: 'ground-truth',
            trackId: 'track-0'
        });
    });

    it('omits the track ID for an untracked annotation', () => {
        const tooltip = createCuboidTooltip({
            annotation: { ...createAnnotationFixture(), trackId: null },
            annotationClassName: 'Vehicle'
        });

        expect(tooltip.trackId).toBeNull();
    });
});
