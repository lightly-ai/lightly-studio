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

        const result = findNavigationPath(root, 'root');
        expect(result).toEqual([root]);

        const result = findNavigationPath(root, 'child-1');
        expect(result).toEqual([root, child1, grandchild]);

        const result = findNavigationPath(root, 'child-2');
        expect(result).toEqual([root, child2]);

        const result = findNavigationPath(root, 'grandchild');
        expect(result).toEqual([root, child1, grandchild]);
    });
});

describe('buildBreadcrumbLevels', () => {
    const pageId = null;
    const datasetId = 'ds-1';

    it('returns empty array when ancestorPath is null', () => {
        const root = makeCollection('root');
        expect(buildBreadcrumbLevels(null, root, pageId, datasetId)).toEqual([]);
    });

    it('returns single level for root-only path', () => {
        const root = makeCollection('root');
        const levels = buildBreadcrumbLevels([root], root, pageId, datasetId);

        expect(levels).toHaveLength(1);
        expect(levels[0].selected.id).toBe('samples-root');
        expect(levels[0].siblings).toHaveLength(1);
        expect(levels[0].siblings[0].id).toBe('samples-root');
    });

    it('returns two levels for root > child path', () => {
        const child1 = makeCollection('child-1', SampleType.VIDEO);
        const child2 = makeCollection('child-2', SampleType.ANNOTATION);
        const root = makeCollection('root', SampleType.IMAGE, [child1, child2]);

        const levels = buildBreadcrumbLevels([root, child1], root, pageId, datasetId);

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

        const levels = buildBreadcrumbLevels([root, child, grandchild], root, pageId, datasetId);

        expect(levels).toHaveLength(3);
        expect(levels[2].selected.id).toBe('frames-gc');
        expect(levels[2].siblings.map((s) => s.id)).toEqual(['frames-gc']);
    });
});
