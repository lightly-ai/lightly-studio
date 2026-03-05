import { describe, it, expect } from 'vitest';
import { findNavigationPath, buildBreadcrumbLevels, getMenuItem } from './utils';
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

describe('getMenuItem', () => {
    it.each([
        [SampleType.IMAGE, 'Images', 'image-col-id'],
        [SampleType.VIDEO, 'Videos', 'video-col-id'],
        [SampleType.VIDEO_FRAME, 'Frames', 'video_frame-col-id'],
        [SampleType.ANNOTATION, 'Annotations', 'annotation-col-id'],
        [SampleType.CAPTION, 'Captions', 'caption-col-id'],
        [SampleType.GROUP, 'Groups', 'group-col-id']
    ] as const)('%s returns correct title, and id', (sampleType, expectedTitle, expectedId) => {
        const item = getMenuItem('dataset-id', undefined, 'col-id', sampleType);
        expect(item.title).toBe(expectedTitle);
        expect(item.id).toBe(expectedId);
    });

    it('uses groupComponentName as title when provided', () => {
        const item = getMenuItem(
            'dataset-id',
            undefined,
            'col-id',
            SampleType.IMAGE,
            'Group Component Name'
        );
        expect(item.title).toBe('Group Component Name');
    });

    it('sets isSelected when collectionId matches currentCollectionId', () => {
        const selected = getMenuItem('dataset-id', 'col-id', 'col-id', SampleType.IMAGE);
        const notSelected = getMenuItem('dataset-id', 'other-col-id', 'col-id', SampleType.IMAGE);
        expect(selected.isSelected).toBe(true);
        expect(notSelected.isSelected).toBe(false);
    });

    it('generates correct href', () => {
        const item = getMenuItem('dataset-id', 'current-col-id', 'col-id', SampleType.IMAGE);
        expect(item.href).toBe('/datasets/dataset-id/image/col-id/samples');
    });
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
    it('returns empty array when ancestorPath is null', () => {
        const root = makeCollection('root');
        expect(buildBreadcrumbLevels(null, root, undefined, 'dataset-id')).toEqual([]);
    });

    it('returns single level for root-only path', () => {
        const root = makeCollection('root');
        const levels = buildBreadcrumbLevels([root], root, 'root', 'dataset-id');

        expect(levels).toHaveLength(1);
        expect(levels[0].selected.id).toBe('image-root');
        expect(levels[0].siblings).toHaveLength(1);
        expect(levels[0].siblings[0].id).toBe('image-root');
    });

    it('returns two levels for root > child path', () => {
        const child1 = makeCollection('child-1', SampleType.VIDEO);
        const child2 = makeCollection('child-2', SampleType.ANNOTATION);
        const root = makeCollection('root', SampleType.IMAGE, [child1, child2]);

        const levels = buildBreadcrumbLevels([root, child1], root, 'child-1', 'dataset-id');

        expect(levels).toHaveLength(2);
        expect(levels[0].selected.id).toBe('image-root');
        expect(levels[1].selected.id).toBe('video-child-1');
        expect(levels[1].siblings.map((s) => s.id)).toEqual([
            'video-child-1',
            'annotation-child-2'
        ]);
    });

    it('returns three levels for deeply nested path', () => {
        const grandchild = makeCollection('gc', SampleType.VIDEO_FRAME);
        const child = makeCollection('child', SampleType.VIDEO, [grandchild]);
        const root = makeCollection('root', SampleType.IMAGE, [child]);

        const levels = buildBreadcrumbLevels([root, child, grandchild], root, 'gc', 'dataset-id');

        expect(levels).toHaveLength(3);
        expect(levels[2].selected.id).toBe('video_frame-gc');
        expect(levels[2].siblings.map((s) => s.id)).toEqual(['video_frame-gc']);
    });

    it('only highlights the matching collection when siblings share the same type', () => {
        const img1 = makeCollection('img-1', SampleType.IMAGE);
        const img2 = makeCollection('img-2', SampleType.IMAGE);
        const root = makeCollection('root', SampleType.GROUP, [img1, img2]);

        const levels = buildBreadcrumbLevels([root, img1], root, 'img-1', 'dataset-id');

        expect(levels[1].siblings).toHaveLength(2);
        const [sib1, sib2] = levels[1].siblings;
        expect(sib1.id).toBe('image-img-1');
        expect(sib1.isSelected).toBe(true);
        expect(sib2.id).toBe('image-img-2');
        expect(sib2.isSelected).toBe(false);
    });
});
