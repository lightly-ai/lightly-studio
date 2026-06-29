import { describe, expect, it } from 'vitest';
import { buildRequestBody } from './buildRequestBody';

type Params = Parameters<typeof buildRequestBody>[0];

describe('buildRequestBody', () => {
    describe('pagination', () => {
        it('uses pageParam as cursor', () => {
            const result = buildRequestBody({ collection_id: 'col-1' }, 40);
            expect(result.pagination.cursor).toBe(40);
        });

        it('defaults limit to 100', () => {
            const result = buildRequestBody({ collection_id: 'col-1' }, 0);
            expect(result.pagination.limit).toBe(100);
        });

        it('uses custom limit when provided', () => {
            const result = buildRequestBody({ collection_id: 'col-1', limit: 50 }, 0);
            expect(result.pagination.limit).toBe(50);
        });
    });

    describe('filters', () => {
        it('returns base body when no filters provided', () => {
            const result = buildRequestBody({ collection_id: 'col-1' }, 0);
            expect(result.annotation_label_ids).toBeUndefined();
            expect(result.tag_ids).toBeUndefined();
            expect(result.sample_ids).toBeUndefined();
            expect(result.text_embedding).toBeUndefined();
        });

        it('propagates annotation_label_ids', () => {
            const params: Params = {
                collection_id: 'col-1',
                annotation_label_ids: ['lbl-1', 'lbl-2']
            };

            const result = buildRequestBody(params, 0);

            expect(result.annotation_label_ids).toEqual(['lbl-1', 'lbl-2']);
        });

        it('propagates tag_ids', () => {
            const result = buildRequestBody({ collection_id: 'col-1', tag_ids: ['t1', 't2'] }, 0);
            expect(result.tag_ids).toEqual(['t1', 't2']);
        });

        it('propagates sample_ids', () => {
            const result = buildRequestBody(
                { collection_id: 'col-1', sample_ids: ['s1', 's2'] },
                0
            );
            expect(result.sample_ids).toEqual(['s1', 's2']);
        });

        it('propagates text_embedding', () => {
            const result = buildRequestBody(
                { collection_id: 'col-1', text_embedding: [0.1, 0.2] },
                0
            );
            expect(result.text_embedding).toEqual([0.1, 0.2]);
        });

        it('propagates all filters together', () => {
            const params: Params = {
                collection_id: 'col-1',
                annotation_label_ids: ['lbl-1'],
                tag_ids: ['t1'],
                sample_ids: ['s1'],
                text_embedding: [1.0, 0.0]
            };

            const result = buildRequestBody(params, 0);

            expect(result).toEqual({
                pagination: { cursor: 0, limit: 100 },
                annotation_label_ids: ['lbl-1'],
                tag_ids: ['t1'],
                sample_ids: ['s1'],
                text_embedding: [1.0, 0.0]
            });
        });
    });
});
