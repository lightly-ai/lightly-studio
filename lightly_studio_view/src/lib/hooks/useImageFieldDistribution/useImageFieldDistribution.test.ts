import { describe, expect, it } from 'vitest';
import {
    fromImageFieldId,
    getImageFieldHistogramRequestOptions,
    selectImageFieldDistributions,
    toImageFieldId
} from './useImageFieldDistribution';

describe('toImageFieldId and fromImageFieldId', () => {
    it('maps an image field to its group ID and back', () => {
        expect(toImageFieldId('width')).toBe('image:width');
        expect(fromImageFieldId('image:width')).toBe('width');
    });

    it('does not treat a metadata key with the same name as an image field', () => {
        expect(fromImageFieldId('width')).toBeUndefined();
    });
});

describe('selectImageFieldDistributions', () => {
    it('keys the histograms by group ID', () => {
        expect(
            selectImageFieldDistributions({
                width: { bin_edges: [100, 200, 300], counts: [5, 1] }
            })
        ).toEqual({ 'image:width': { binEdges: [100, 200, 300], counts: [5, 1] } });
    });

    it('returns an empty record while the query has no data yet', () => {
        expect(selectImageFieldDistributions(undefined)).toEqual({});
    });
});

describe('getImageFieldHistogramRequestOptions', () => {
    it('puts the filter, bin count and fields in the request body', () => {
        const filter = { filter_type: 'image' as const, width: { min: 100 } };

        expect(
            getImageFieldHistogramRequestOptions({
                collectionId: 'collection-id',
                filter,
                binCount: 50,
                fields: ['height']
            })
        ).toEqual({
            path: { collection_id: 'collection-id' },
            body: { filters: filter, bin_count: 50, fields: ['height'] }
        });
    });
});
