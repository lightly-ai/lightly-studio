import { describe, expect, it } from 'vitest';
import { patchFilters } from './patchFilters';

interface Params {
    collection_id: string;
    filters?: { sample_ids?: string[]; tag_ids?: string[] };
}

describe('patchFilters', () => {
    it('merges the patch into filters', () => {
        const params: Params = { collection_id: 'c', filters: { tag_ids: ['t'] } };
        expect(patchFilters(params, { sample_ids: ['s'] })).toEqual({
            collection_id: 'c',
            filters: { tag_ids: ['t'], sample_ids: ['s'] }
        });
    });

    it('creates filters when missing', () => {
        const params: Params = { collection_id: 'c' };
        expect(patchFilters(params, { sample_ids: ['s'] })).toEqual({
            collection_id: 'c',
            filters: { sample_ids: ['s'] }
        });
    });

    it('keeps undefined values as keys', () => {
        const params: Params = { collection_id: 'c', filters: { sample_ids: ['s'] } };
        const result = patchFilters(params, { sample_ids: undefined });
        expect(Object.keys(result.filters ?? {})).toEqual(['sample_ids']);
        expect(result.filters?.sample_ids).toBeUndefined();
    });

    it('does not mutate params', () => {
        const params: Params = { collection_id: 'c', filters: { tag_ids: ['t'] } };
        const copy = structuredClone(params);
        patchFilters(params, { sample_ids: ['s'] });
        expect(params).toEqual(copy);
    });
});
