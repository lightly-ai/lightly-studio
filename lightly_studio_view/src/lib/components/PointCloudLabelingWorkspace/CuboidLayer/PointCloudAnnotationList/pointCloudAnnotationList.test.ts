import { describe, it, expect } from 'vitest';
import { createAnnotationFixture } from '$lib/components/PointCloudLabelingWorkspace/domain/fixtures';
import {
    groupAnnotationsBySource,
    resolveAnnotationClassName,
    buildAnnotationForest,
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

describe('groupAnnotationsBySource — ordering', () => {
    it('places each parent before its children, children sorted by trackNumber', () => {
        const truck1 = {
            ...createAnnotationFixture(),
            id: 'a-truck1',
            annotationSourceId: 'gt',
            trackNumber: 1,
            parentTrackNumber: null
        };
        const cabin1 = {
            ...createAnnotationFixture(),
            id: 'a-cabin1',
            annotationSourceId: 'gt',
            trackNumber: 8,
            parentTrackNumber: 1
        };
        const bed1 = {
            ...createAnnotationFixture(),
            id: 'a-bed1',
            annotationSourceId: 'gt',
            trackNumber: 5,
            parentTrackNumber: 1
        };
        const truck2 = {
            ...createAnnotationFixture(),
            id: 'a-truck2',
            annotationSourceId: 'gt',
            trackNumber: 2,
            parentTrackNumber: null
        };
        const cabin2 = {
            ...createAnnotationFixture(),
            id: 'a-cabin2',
            annotationSourceId: 'gt',
            trackNumber: 9,
            parentTrackNumber: 2
        };
        const sources = [{ id: 'gt', name: 'Ground Truth' }];

        const groups = groupAnnotationsBySource({
            cuboids: [cabin1, truck2, bed1, cabin2, truck1],
            sources
        });

        expect(groups[0].cuboids.map((c) => [c.parentTrackNumber, c.trackNumber])).toEqual([
            [null, 1], // truck 1
            [1, 5], // bed 1 (child of truck 1)
            [1, 8], // cabin 1 (child of truck 1)
            [null, 2], // truck 2
            [2, 9] // cabin 2 (child of truck 2)
        ]);
    });

    it('places cuboids with null track number at the end within their parent group', () => {
        const cuboid1 = {
            ...createAnnotationFixture(),
            id: 'a-1',
            annotationSourceId: 'gt',
            trackNumber: 2,
            parentTrackNumber: null
        };
        const cuboid2 = {
            ...createAnnotationFixture(),
            id: 'a-2',
            annotationSourceId: 'gt',
            trackNumber: null,
            parentTrackNumber: null
        };
        const cuboid3 = {
            ...createAnnotationFixture(),
            id: 'a-3',
            annotationSourceId: 'gt',
            trackNumber: 1,
            parentTrackNumber: null
        };
        const sources = [{ id: 'gt', name: 'Ground Truth' }];

        const groups = groupAnnotationsBySource({ cuboids: [cuboid1, cuboid2, cuboid3], sources });

        expect(groups[0].cuboids.map((c) => c.trackNumber)).toEqual([1, 2, null]);
    });

    it('recursively emits descendants before moving to the next top-level track', () => {
        const grandparent = {
            ...createAnnotationFixture(),
            id: 'a-gp',
            annotationSourceId: 'gt',
            trackNumber: 1,
            parentTrackNumber: null
        };
        const parent = {
            ...createAnnotationFixture(),
            id: 'a-p',
            annotationSourceId: 'gt',
            trackNumber: 2,
            parentTrackNumber: 1
        };
        const grandchild = {
            ...createAnnotationFixture(),
            id: 'a-gc',
            annotationSourceId: 'gt',
            trackNumber: 3,
            parentTrackNumber: 2
        };
        const uncle = {
            ...createAnnotationFixture(),
            id: 'a-uncle',
            annotationSourceId: 'gt',
            trackNumber: 10,
            parentTrackNumber: null
        };
        const sources = [{ id: 'gt', name: 'Ground Truth' }];

        const groups = groupAnnotationsBySource({
            cuboids: [uncle, grandchild, parent, grandparent],
            sources
        });

        expect(groups[0].cuboids.map((c) => c.trackNumber)).toEqual([1, 2, 3, 10]);
    });

    it('sorts independently within each source group', () => {
        const cuboid1 = {
            ...createAnnotationFixture(),
            id: 'a-1',
            annotationSourceId: 'gt',
            trackNumber: 5,
            parentTrackNumber: null
        };
        const cuboid2 = {
            ...createAnnotationFixture(),
            id: 'a-2',
            annotationSourceId: 'gt',
            trackNumber: 1,
            parentTrackNumber: null
        };
        const cuboid3 = {
            ...createAnnotationFixture(),
            id: 'a-3',
            annotationSourceId: 'pred',
            trackNumber: 4,
            parentTrackNumber: null
        };
        const cuboid4 = {
            ...createAnnotationFixture(),
            id: 'a-4',
            annotationSourceId: 'pred',
            trackNumber: 2,
            parentTrackNumber: null
        };
        const sources = [
            { id: 'gt', name: 'Ground Truth' },
            { id: 'pred', name: 'Predictions' }
        ];

        const groups = groupAnnotationsBySource({
            cuboids: [cuboid1, cuboid2, cuboid3, cuboid4],
            sources
        });

        expect(groups[0].cuboids.map((c) => c.trackNumber)).toEqual([1, 5]);
        expect(groups[1].cuboids.map((c) => c.trackNumber)).toEqual([2, 4]);
    });
});

describe('buildAnnotationForest', () => {
    it('wraps a childless root in the no-parent-track group', () => {
        const root = {
            ...createAnnotationFixture(),
            id: 'root',
            trackNumber: 1,
            parentTrackNumber: null
        };

        const forest = buildAnnotationForest({ cuboids: [root] });

        expect(forest).toHaveLength(1);
        expect(forest[0].cuboid).toBeNull();
        expect(forest[0].children).toHaveLength(1);
        expect(forest[0].children[0].cuboid).toBe(root);
    });

    it('nests children under their parent root', () => {
        const truck = {
            ...createAnnotationFixture(),
            id: 'truck',
            trackNumber: 1,
            parentTrackNumber: null
        };
        const cabin = {
            ...createAnnotationFixture(),
            id: 'cabin',
            trackNumber: 2,
            parentTrackNumber: 1
        };
        const trailer = {
            ...createAnnotationFixture(),
            id: 'trailer',
            trackNumber: 3,
            parentTrackNumber: 1
        };

        const forest = buildAnnotationForest({ cuboids: [truck, cabin, trailer] });

        expect(forest).toHaveLength(1);
        expect(forest[0].cuboid).toBe(truck);
        expect(forest[0].children).toHaveLength(2);
        expect(forest[0].children[0].cuboid).toBe(cabin);
        expect(forest[0].children[1].cuboid).toBe(trailer);
        expect(forest[0].subtreeSize).toBe(3);
    });

    it('counts subtree size recursively for multi-level nesting', () => {
        const grandparent = {
            ...createAnnotationFixture(),
            id: 'gp',
            trackNumber: 1,
            parentTrackNumber: null
        };
        const parent = {
            ...createAnnotationFixture(),
            id: 'p',
            trackNumber: 2,
            parentTrackNumber: 1
        };
        const grandchild = {
            ...createAnnotationFixture(),
            id: 'gc',
            trackNumber: 3,
            parentTrackNumber: 2
        };

        const forest = buildAnnotationForest({ cuboids: [grandparent, parent, grandchild] });

        expect(forest[0].subtreeSize).toBe(3);
        expect(forest[0].children[0].subtreeSize).toBe(2);
        expect(forest[0].children[0].children[0].subtreeSize).toBe(1);
    });

    it('wraps a root with null trackNumber in the no-parent-track group', () => {
        const nullTrack = {
            ...createAnnotationFixture(),
            id: 'null-track',
            trackNumber: null,
            parentTrackNumber: null
        };

        const forest = buildAnnotationForest({ cuboids: [nullTrack] });

        expect(forest).toHaveLength(1);
        expect(forest[0].cuboid).toBeNull();
        expect(forest[0].children).toHaveLength(1);
        expect(forest[0].children[0].cuboid).toBe(nullTrack);
    });

    it('places parent root and childless root in separate groups', () => {
        const root1 = {
            ...createAnnotationFixture(),
            id: 'root1',
            trackNumber: 1,
            parentTrackNumber: null
        };
        const child1 = {
            ...createAnnotationFixture(),
            id: 'child1',
            trackNumber: 2,
            parentTrackNumber: 1
        };
        const root2 = {
            ...createAnnotationFixture(),
            id: 'root2',
            trackNumber: 10,
            parentTrackNumber: null
        };

        const forest = buildAnnotationForest({ cuboids: [root1, child1, root2] });

        expect(forest).toHaveLength(2);
        expect(forest[0].cuboid).toBe(root1);
        expect(forest[0].children[0].cuboid).toBe(child1);
        expect(forest[1].cuboid).toBeNull();
        expect(forest[1].children[0].cuboid).toBe(root2);
    });

    it('places absent-parent orphan and standalone root in separate groups', () => {
        const root = {
            ...createAnnotationFixture(),
            id: 'root',
            trackNumber: 1,
            parentTrackNumber: null
        };
        const orphan = {
            ...createAnnotationFixture(),
            id: 'orphan',
            trackNumber: 5,
            parentTrackNumber: 99,
            parentTrackClassName: 'truck'
        };

        const forest = buildAnnotationForest({ cuboids: [root, orphan] });

        expect(forest).toHaveLength(2);
        expect(forest[0].cuboid).toBeNull();
        expect(forest[0].children[0].cuboid).toBe(orphan);
        expect(forest[1].cuboid).toBeNull();
        expect(forest[1].children[0].cuboid).toBe(root);
    });

    it('groups orphan with parentTrackClassName under absent parent node', () => {
        const cabin = {
            ...createAnnotationFixture(),
            id: 'cabin',
            trackNumber: 2,
            parentTrackNumber: 1,
            parentTrackClassName: 'truck'
        };

        const forest = buildAnnotationForest({ cuboids: [cabin] });

        expect(forest).toHaveLength(1);
        expect(forest[0].cuboid).toBeNull();
        expect(forest[0].children).toHaveLength(1);
        expect(forest[0].children[0].cuboid).toBe(cabin);
        expect(forest[0].subtreeSize).toBe(1);
    });

    it('groups multiple orphans sharing the same absent parent', () => {
        const cabin = {
            ...createAnnotationFixture(),
            id: 'cabin',
            trackNumber: 2,
            parentTrackNumber: 1,
            parentTrackClassName: 'truck'
        };
        const bed = {
            ...createAnnotationFixture(),
            id: 'bed',
            trackNumber: 3,
            parentTrackNumber: 1,
            parentTrackClassName: 'truck'
        };

        const forest = buildAnnotationForest({ cuboids: [cabin, bed] });

        expect(forest).toHaveLength(1);
        expect(forest[0].cuboid).toBeNull();
        expect(forest[0].children).toHaveLength(2);
        expect(forest[0].subtreeSize).toBe(2);
    });

    it('handles multi-level nesting with absent intermediate', () => {
        const truck = {
            ...createAnnotationFixture(),
            id: 'truck',
            trackNumber: 1,
            parentTrackNumber: null
        };
        const window = {
            ...createAnnotationFixture(),
            id: 'window',
            trackNumber: 3,
            parentTrackNumber: 2,
            parentTrackClassName: 'cabin'
        };

        const forest = buildAnnotationForest({ cuboids: [truck, window] });

        expect(forest).toHaveLength(2);
        expect(forest[0].cuboid).toBeNull();
        expect(forest[0].children).toHaveLength(1);
        expect(forest[0].children[0].cuboid).toBe(window);
        expect(forest[1].cuboid).toBeNull();
        expect(forest[1].children).toHaveLength(1);
        expect(forest[1].children[0].cuboid).toBe(truck);
    });

    it('places absent parent groups after present parents, standalone roots in no-parent-track group', () => {
        const truck = {
            ...createAnnotationFixture(),
            id: 'truck',
            trackNumber: 1,
            parentTrackNumber: null
        };
        const truckChild = {
            ...createAnnotationFixture(),
            id: 'truck-cabin',
            trackNumber: 10,
            parentTrackNumber: 1
        };
        const absentChild = {
            ...createAnnotationFixture(),
            id: 'absent-cabin',
            trackNumber: 20,
            parentTrackNumber: 99,
            parentTrackClassName: 'bus'
        };
        const standalone = {
            ...createAnnotationFixture(),
            id: 'car',
            trackNumber: 50,
            parentTrackNumber: null
        };

        const forest = buildAnnotationForest({
            cuboids: [truck, truckChild, absentChild, standalone]
        });

        expect(forest).toHaveLength(3);
        expect(forest[0].cuboid).toBe(truck);
        expect(forest[0].children).toHaveLength(1);
        expect(forest[1].cuboid).toBeNull();
        expect(forest[1].children[0].cuboid).toBe(absentChild);
        expect(forest[2].cuboid).toBeNull();
        expect(forest[2].children[0].cuboid).toBe(standalone);
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
