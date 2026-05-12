import { describe, expect, it, vi } from 'vitest';
import { buildRequestBody, type ImagesInfiniteParams } from './useImagesInfinite';

vi.mock('$lib/hooks/useMetadataFilters/useMetadataFilters', () => ({
    createMetadataFilters: vi.fn(() => [])
}));

describe('buildRequestBody', () => {
    it('propagates collection_ids to annotations_filter', () => {
        const params: ImagesInfiniteParams = {
            collection_id: 'col-1',
            mode: 'normal',
            filters: { collection_ids: ['coll-1', 'coll-2'] }
        };

        const result = buildRequestBody(params, 0);

        expect(result.filters?.sample_filter?.annotations_filter).toEqual({
            collection_ids: ['coll-1', 'coll-2'],
            filter_type: 'annotations'
        });
    });

    it('omits annotations_filter when collection_ids is empty', () => {
        const params: ImagesInfiniteParams = {
            collection_id: 'col-1',
            mode: 'normal',
            filters: { collection_ids: [] }
        };

        const result = buildRequestBody(params, 0);

        expect(result.filters?.sample_filter?.annotations_filter).toBeUndefined();
    });

    it('propagates both annotation_label_ids and collection_ids', () => {
        const params: ImagesInfiniteParams = {
            collection_id: 'col-1',
            mode: 'normal',
            filters: {
                annotation_label_ids: ['lbl-1'],
                collection_ids: ['coll-1']
            }
        };

        const result = buildRequestBody(params, 0);

        expect(result.filters?.sample_filter?.annotations_filter).toEqual({
            annotation_label_ids: ['lbl-1'],
            collection_ids: ['coll-1'],
            filter_type: 'annotations'
        });
    });
});
