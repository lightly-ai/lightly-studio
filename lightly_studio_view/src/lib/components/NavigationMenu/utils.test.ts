import { describe, it, expect } from 'vitest';
import { findAncestorPath, buildBreadcrumbLevels } from './utils';
import { SampleType, type CollectionView } from '$lib/api/lightly_studio_local';
import type { NavigationMenuItem } from './types';

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

describe('findAncestorPath', () => {
    it('returns [root] when target is root', () => {
        const root = makeCollection('root');
        const result = findAncestorPath(root, 'root');
        expect(result).toEqual([root]);
    });

    it('returns [root, child] when target is a direct child', () => {
        const child = makeCollection('child', SampleType.VIDEO);
        const root = makeCollection('root', SampleType.IMAGE, [child]);

        const result = findAncestorPath(root, 'child');
        expect(result).toEqual([root, child]);
    });

    it('returns full path for deeply nested target', () => {
        const grandchild = makeCollection('grandchild', SampleType.VIDEO_FRAME);
        const child = makeCollection('child', SampleType.VIDEO, [grandchild]);
        const root = makeCollection('root', SampleType.IMAGE, [child]);

        const result = findAncestorPath(root, 'grandchild');
        expect(result).toEqual([root, child, grandchild]);
    });

    it('returns null when target is not found', () => {
        const child = makeCollection('child', SampleType.VIDEO);
        const root = makeCollection('root', SampleType.IMAGE, [child]);

        const result = findAncestorPath(root, 'nonexistent');
        expect(result).toBeNull();
    });

    it('finds target among multiple siblings', () => {
        const child1 = makeCollection('child-1', SampleType.VIDEO);
        const child2 = makeCollection('child-2', SampleType.ANNOTATION);
        const root = makeCollection('root', SampleType.IMAGE, [child1, child2]);

        const result = findAncestorPath(root, 'child-2');
        expect(result).toEqual([root, child2]);
    });

    it('returns null when root has no children and target is different', () => {
        const root = makeCollection('root');
        const result = findAncestorPath(root, 'other');
        expect(result).toBeNull();
    });
});

describe('buildBreadcrumbLevels', () => {
    const toMenuItem = (c: CollectionView): NavigationMenuItem => ({
        title: c.name,
        id: c.collection_id,
        href: `/${c.collection_id}`,
        isSelected: false
    });

    it('returns empty array when ancestorPath is null', () => {
        const root = makeCollection('root');
        expect(buildBreadcrumbLevels(null, root, toMenuItem)).toEqual([]);
    });

    it('returns single level for root-only path', () => {
        const root = makeCollection('root');
        const levels = buildBreadcrumbLevels([root], root, toMenuItem);

        expect(levels).toHaveLength(1);
        expect(levels[0].selected.id).toBe('root');
        expect(levels[0].siblings).toHaveLength(1);
        expect(levels[0].siblings[0].id).toBe('root');
    });

    it('returns two levels for root > child path', () => {
        const child1 = makeCollection('child-1', SampleType.VIDEO);
        const child2 = makeCollection('child-2', SampleType.ANNOTATION);
        const root = makeCollection('root', SampleType.IMAGE, [child1, child2]);

        const levels = buildBreadcrumbLevels([root, child1], root, toMenuItem);

        expect(levels).toHaveLength(2);
        expect(levels[0].selected.id).toBe('root');
        expect(levels[1].selected.id).toBe('child-1');
        expect(levels[1].siblings.map((s) => s.id)).toEqual(['child-1', 'child-2']);
    });

    it('returns three levels for deeply nested path', () => {
        const grandchild = makeCollection('gc', SampleType.VIDEO_FRAME);
        const child = makeCollection('child', SampleType.VIDEO, [grandchild]);
        const root = makeCollection('root', SampleType.IMAGE, [child]);

        const levels = buildBreadcrumbLevels([root, child, grandchild], root, toMenuItem);

        expect(levels).toHaveLength(3);
        expect(levels[2].selected.id).toBe('gc');
        expect(levels[2].siblings.map((s) => s.id)).toEqual(['gc']);
    });
});
