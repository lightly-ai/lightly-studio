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
            filters: { collection_ids: ['label-1', 'label-2'] }
        };

        const result = buildRequestBody(params, 0);

        expect(result.filters?.sample_filter?.annotations_filter).toEqual({
            collection_ids: ['label-1', 'label-2']
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
});
