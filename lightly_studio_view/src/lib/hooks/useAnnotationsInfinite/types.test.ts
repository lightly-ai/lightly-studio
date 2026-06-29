import { describe, expect, it } from 'vitest';
import { toAnnotationsInfiniteParams } from './types';

describe('toAnnotationsInfiniteParams', () => {
    it('maps path.collection_id to collection_id', () => {
        const result = toAnnotationsInfiniteParams({
            path: { collection_id: 'col-1' }
        });
        expect(result.collection_id).toBe('col-1');
    });

    it('spreads query fields onto params', () => {
        const result = toAnnotationsInfiniteParams({
            path: { collection_id: 'col-1' },
            query: {
                annotation_label_ids: ['lbl-1'],
                tag_ids: ['t1'],
                sample_ids: ['s1'],
                text_embedding: [0.1],
                limit: 25
            }
        });

        expect(result).toEqual({
            collection_id: 'col-1',
            annotation_label_ids: ['lbl-1'],
            tag_ids: ['t1'],
            sample_ids: ['s1'],
            text_embedding: [0.1],
            limit: 25
        });
    });

    it('omits query fields when query is undefined', () => {
        const result = toAnnotationsInfiniteParams({
            path: { collection_id: 'col-1' }
        });

        expect(result).toEqual({ collection_id: 'col-1' });
    });
});
