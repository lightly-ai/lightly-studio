import { describe, expect, it } from 'vitest';
import { load } from './+page';

describe('point-cloud sample page load', () => {
    it('maps route and query parameters to page data', async () => {
        const result = await load({
            params: {
                dataset_id: 'dataset',
                collection_id: 'collection',
                sample_id: 'sample'
            },
            url: new URL(
                'http://localhost/datasets/dataset/point-clouds/collection/sample?collection_type=group&sequence_id=sequence&group_id=group'
            )
        } as Parameters<typeof load>[0]);

        expect(result).toEqual({
            datasetId: 'dataset',
            collectionType: 'group',
            collectionId: 'collection',
            sampleId: 'sample',
            sequenceId: 'sequence',
            groupId: 'group'
        });
    });

    it('leaves optional query values undefined when absent', async () => {
        const result = await load({
            params: {
                dataset_id: 'dataset',
                collection_id: 'collection',
                sample_id: 'sample'
            },
            url: new URL('http://localhost/datasets/dataset/point-clouds/collection/sample')
        } as Parameters<typeof load>[0]);

        expect(result).toEqual({
            datasetId: 'dataset',
            collectionType: undefined,
            collectionId: 'collection',
            sampleId: 'sample',
            sequenceId: undefined,
            groupId: undefined
        });
    });
});
