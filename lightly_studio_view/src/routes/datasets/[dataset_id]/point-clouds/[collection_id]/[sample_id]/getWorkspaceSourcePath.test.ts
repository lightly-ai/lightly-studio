import { describe, it, expect } from 'vitest';
import { SampleType } from '$lib/api/lightly_studio_local';
import { getWorkspaceSourcePath } from './getWorkspaceSourcePath';

const collection = {
    collection_id: 'collection-1',
    name: 'Recordings',
    sample_type: SampleType.MCAP
};

describe('getWorkspaceSourcePath', () => {
    it('links the collection back to the point-clouds grid by default', () => {
        expect(getWorkspaceSourcePath({ datasetId: 'dataset-1', collection })).toEqual([
            { label: 'Home', href: '/' },
            {
                label: 'Recordings',
                href: '/datasets/dataset-1/mcap/collection-1/point-clouds'
            },
            { label: 'Sequence' }
        ]);
    });

    it('links the collection back to the groups grid when opened from a group', () => {
        const [, collectionCrumb] = getWorkspaceSourcePath({
            datasetId: 'dataset-1',
            collection,
            collectionType: 'group'
        });

        expect(collectionCrumb.href).toBe('/datasets/dataset-1/group/collection-1/groups');
    });
});
