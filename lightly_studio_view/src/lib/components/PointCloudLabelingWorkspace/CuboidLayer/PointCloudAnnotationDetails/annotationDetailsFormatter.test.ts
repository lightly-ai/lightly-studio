import { describe, it, expect } from 'vitest';
import { createAnnotationFixture } from '$lib/components/PointCloudLabelingWorkspace/domain/fixtures';
import { createAnnotationDetails } from './pointCloudAnnotationDetails';

describe('createAnnotationDetails', () => {
    it('formats location as per-axis strings with fixed precision', () => {
        const details = createAnnotationDetails({
            annotation: {
                ...createAnnotationFixture(),
                center: [10, -2, 1.234]
            }
        });

        expect(details.location).toEqual(['10.00', '-2.00', '1.23']);
    });

    it('formats dimensions as per-axis strings', () => {
        const details = createAnnotationDetails({
            annotation: {
                ...createAnnotationFixture(),
                size: [4.5, 1.8, 1.5]
            }
        });

        expect(details.dimensions).toEqual(['4.50', '1.80', '1.50']);
    });

    it('converts quaternion rotation to euler degrees per axis', () => {
        const details = createAnnotationDetails({
            annotation: {
                ...createAnnotationFixture(),
                rotation: [0, 0, Math.sin(Math.PI / 8), Math.cos(Math.PI / 8)]
            }
        });

        expect(details.rotation).toEqual(['0.0', '0.0', '45.0']);
    });

    it('passes through annotation source id', () => {
        const details = createAnnotationDetails({ annotation: createAnnotationFixture() });

        expect(details.annotationSourceId).toBe('ground-truth');
    });

    it('passes through track id when present', () => {
        const details = createAnnotationDetails({ annotation: createAnnotationFixture() });

        expect(details.trackId).toBe('track-0');
    });

    it('passes through null track id for untracked annotations', () => {
        const details = createAnnotationDetails({
            annotation: { ...createAnnotationFixture(), trackId: null }
        });

        expect(details.trackId).toBeNull();
    });
});
