import { describe, it, expect } from 'vitest';
import { findAncestorPath } from './utils';
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
