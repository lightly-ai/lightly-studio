import { describe, expect, it } from 'vitest';
import type { CollectionView } from '$lib/api/lightly_studio_local';
import { SampleType } from '$lib/api/lightly_studio_local';
import { buildSidebarNavItems } from './buildSidebarNavItems';

const annotationChild = {
    collection_id: 'annotations-id',
    dataset_id: 'dataset-id',
    name: 'annotation',
    sample_type: SampleType.ANNOTATION,
    children: []
} as unknown as CollectionView;

const rootCollection = {
    collection_id: 'images-id',
    dataset_id: 'dataset-id',
    name: 'my dataset',
    sample_type: SampleType.IMAGE,
    children: [annotationChild]
} as unknown as CollectionView;

const defaultParams = {
    rootCollection,
    currentCollectionId: 'images-id',
    datasetId: 'dataset-id',
    sampleCount: 128,
    annotationCount: 1188
};

describe('buildSidebarNavItems', () => {
    it('lists the root view followed by its children', () => {
        const items = buildSidebarNavItems(defaultParams);

        expect(items.map((item) => item.title)).toEqual(['Images', 'Annotations']);
    });

    it('marks the open collection as selected', () => {
        const items = buildSidebarNavItems(defaultParams);

        expect(items[0].isSelected).toBe(true);
        expect(items[1].isSelected).toBe(false);
    });

    it('counts samples on the root row and annotations on the annotation row', () => {
        const items = buildSidebarNavItems(defaultParams);

        expect(items[0].count).toBe(128);
        expect(items[1].count).toBe(1188);
    });

    it('leaves a non-annotation child without a count, since none is known', () => {
        const items = buildSidebarNavItems({
            ...defaultParams,
            rootCollection: {
                ...rootCollection,
                children: [
                    { ...annotationChild, sample_type: SampleType.CAPTION, name: 'captions' }
                ]
            } as unknown as CollectionView
        });

        expect(items[1].count).toBeUndefined();
    });

    it('reaches collections nested below a child, like a video dataset captions view', () => {
        const items = buildSidebarNavItems({
            ...defaultParams,
            rootCollection: {
                ...rootCollection,
                children: [
                    {
                        ...annotationChild,
                        sample_type: SampleType.VIDEO_FRAME,
                        name: 'frames',
                        children: [
                            {
                                ...annotationChild,
                                collection_id: 'captions-id',
                                sample_type: SampleType.CAPTION,
                                name: 'captions'
                            }
                        ]
                    }
                ]
            } as unknown as CollectionView
        });

        expect(items.map((item) => item.title)).toEqual(['Images', 'Frames', 'Captions']);
    });

    it('links each row to its collection route', () => {
        const items = buildSidebarNavItems(defaultParams);

        expect(items[0].href).toContain('/images');
        expect(items[1].href).toContain('/annotations');
    });
});
