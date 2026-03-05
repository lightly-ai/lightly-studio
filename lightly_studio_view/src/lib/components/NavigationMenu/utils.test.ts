import { describe, it, expect } from 'vitest';
import { findNavigationPath, buildBreadcrumbLevels } from './utils';
import { SampleType, type CollectionView } from '$lib/api/lightly_studio_local';

const makeCollection = (
    id: string,
    sampleType: SampleType = SampleType.IMAGE,
    children?: CollectionView[]
): CollectionView => ({
    collection_id: id,
    name: id,
    sample_type: sampleType,
    created_at: new Date(),
    updated_at: new Date(),
    children
});

describe('findNavigationPath', () => {
    it('returns null when target is not found', () => {
        const child = makeCollection('child', SampleType.VIDEO);
        const root = makeCollection('root', SampleType.IMAGE, [child]);

        const result = findNavigationPath(root, 'nonexistent');
        expect(result).toBeNull();
    });

    it('extends path from target to leaf via first children', () => {
        const grandchild = makeCollection('grandchild', SampleType.VIDEO_FRAME);
        const child1 = makeCollection('child-1', SampleType.VIDEO, [grandchild]);
        const child2 = makeCollection('child-2', SampleType.ANNOTATION);
        const root = makeCollection('root', SampleType.IMAGE, [child1, child2]);

        const result1 = findNavigationPath(root, 'root');
        expect(result1).toEqual([root, child1, grandchild]);

        const result2 = findNavigationPath(root, 'child-1');
        expect(result2).toEqual([root, child1, grandchild]);

        const result3 = findNavigationPath(root, 'child-2');
        expect(result3).toEqual([root, child2]);

        const result4 = findNavigationPath(root, 'grandchild');
        expect(result4).toEqual([root, child1, grandchild]);
    });
});

describe('buildBreadcrumbLevels', () => {
    const datasetId = 'ds-1';

    it('returns empty array when ancestorPath is null', () => {
        const root = makeCollection('root');
        expect(buildBreadcrumbLevels(null, root, undefined, datasetId)).toEqual([]);
    });

    it('returns single level for root-only path', () => {
        const root = makeCollection('root');
        const levels = buildBreadcrumbLevels([root], root, 'root', datasetId);

        expect(levels).toHaveLength(1);
        expect(levels[0].selected.id).toBe('samples-root');
        expect(levels[0].siblings).toHaveLength(1);
        expect(levels[0].siblings[0].id).toBe('samples-root');
    });

    it('returns two levels for root > child path', () => {
        const child1 = makeCollection('child-1', SampleType.VIDEO);
        const child2 = makeCollection('child-2', SampleType.ANNOTATION);
        const root = makeCollection('root', SampleType.IMAGE, [child1, child2]);

        const levels = buildBreadcrumbLevels([root, child1], root, 'child-1', datasetId);

        expect(levels).toHaveLength(2);
        expect(levels[0].selected.id).toBe('samples-root');
        expect(levels[1].selected.id).toBe('videos-child-1');
        expect(levels[1].siblings.map((s) => s.id)).toEqual([
            'videos-child-1',
            'annotations-child-2'
        ]);
    });

    it('returns three levels for deeply nested path', () => {
        const grandchild = makeCollection('gc', SampleType.VIDEO_FRAME);
        const child = makeCollection('child', SampleType.VIDEO, [grandchild]);
        const root = makeCollection('root', SampleType.IMAGE, [child]);

        const levels = buildBreadcrumbLevels([root, child, grandchild], root, 'gc', datasetId);

        expect(levels).toHaveLength(3);
        expect(levels[2].selected.id).toBe('frames-gc');
        expect(levels[2].siblings.map((s) => s.id)).toEqual(['frames-gc']);
    });

    it('only highlights the matching collection when siblings share the same type', () => {
        const img1 = makeCollection('img-1', SampleType.IMAGE);
        const img2 = makeCollection('img-2', SampleType.IMAGE);
        const root = makeCollection('root', SampleType.GROUP, [img1, img2]);

        const levels = buildBreadcrumbLevels([root, img1], root, 'img-1', datasetId);

        expect(levels[1].siblings).toHaveLength(2);
        const [sib1, sib2] = levels[1].siblings;
        expect(sib1.id).toBe('samples-img-1');
        expect(sib1.isSelected).toBe(true);
        expect(sib2.id).toBe('samples-img-2');
        expect(sib2.isSelected).toBe(false);
    });
});
