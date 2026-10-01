import { describe, it, expect } from 'vitest';
import { createAnnotationFixture } from '$lib/components/PointCloudLabelingWorkspace/domain/fixtures';
import {
    groupAnnotationsBySource,
    resolveAnnotationClassName,
    UNKNOWN_SOURCE_NAME
} from './pointCloudAnnotationList';

describe('groupAnnotationsBySource', () => {
    it('returns a single group when all cuboids share one source', () => {
        const cuboid1 = { ...createAnnotationFixture(), id: 'a-1', annotationSourceId: 'gt' };
        const cuboid2 = { ...createAnnotationFixture(), id: 'a-2', annotationSourceId: 'gt' };
        const sources = [{ id: 'gt', name: 'Ground Truth' }];

        const groups = groupAnnotationsBySource({ cuboids: [cuboid1, cuboid2], sources });

        expect(groups).toEqual([
            { sourceId: 'gt', sourceName: 'Ground Truth', cuboids: [cuboid1, cuboid2] }
        ]);
    });

    it('returns multiple groups ordered by sources array', () => {
        const cuboid1 = { ...createAnnotationFixture(), id: 'a-1', annotationSourceId: 'gt' };
        const cuboid2 = { ...createAnnotationFixture(), id: 'a-2', annotationSourceId: 'pred' };
        const sources = [
            { id: 'gt', name: 'Ground Truth' },
            { id: 'pred', name: 'Predictions' }
        ];

        const groups = groupAnnotationsBySource({ cuboids: [cuboid1, cuboid2], sources });

        expect(groups[0].sourceId).toBe('gt');
        expect(groups[1].sourceId).toBe('pred');
    });

    it('skips sources that have no cuboids', () => {
        const cuboid = { ...createAnnotationFixture(), id: 'a-1', annotationSourceId: 'gt' };
        const sources = [
            { id: 'gt', name: 'Ground Truth' },
            { id: 'pred', name: 'Predictions' }
        ];

        const groups = groupAnnotationsBySource({ cuboids: [cuboid], sources });

        expect(groups).toHaveLength(1);
        expect(groups[0].sourceId).toBe('gt');
    });

    it('appends cuboids with unknown source as a fallback group', () => {
        const cuboid = { ...createAnnotationFixture(), id: 'a-1', annotationSourceId: 'mystery' };
        const sources = [{ id: 'gt', name: 'Ground Truth' }];

        const groups = groupAnnotationsBySource({ cuboids: [cuboid], sources });

        expect(groups).toHaveLength(1);
        expect(groups[0].sourceName).toBe(UNKNOWN_SOURCE_NAME);
        expect(groups[0].cuboids).toEqual([cuboid]);
    });

    it('returns empty array when there are no cuboids', () => {
        const sources = [{ id: 'gt', name: 'Ground Truth' }];

        expect(groupAnnotationsBySource({ cuboids: [], sources })).toEqual([]);
    });
});

describe('resolveAnnotationClassName', () => {
    it('returns the class name when the class is found', () => {
        const classes = [{ id: 'vehicle', name: 'Vehicle', color: '#3366ff' }];

        expect(
            resolveAnnotationClassName({ annotationClasses: classes, annotationClassId: 'vehicle' })
        ).toBe('Vehicle');
    });

    it('falls back to the class id when the class is not found', () => {
        const classes = [{ id: 'vehicle', name: 'Vehicle', color: '#3366ff' }];

        expect(
            resolveAnnotationClassName({
                annotationClasses: classes,
                annotationClassId: 'unknown-id'
            })
        ).toBe('unknown-id');
    });
});
