import { describe, expect, it } from 'vitest';
import { getAnnotationsFilter } from './getAnnotationsFilter';

describe('getAnnotationsFilter', () => {
    it('returns annotation_label_ids when set', () => {
        const result = getAnnotationsFilter({ annotation_label_ids: ['a', 'b'] });
        expect(result).toEqual({ annotation_label_ids: ['a', 'b'], filter_type: 'annotations' });
    });

    it('returns collection_ids when set', () => {
        const result = getAnnotationsFilter({ collection_ids: ['c1', 'c2'] });
        expect(result).toEqual({ collection_ids: ['c1', 'c2'], filter_type: 'annotations' });
    });

    it('returns both fields when both are set', () => {
        const result = getAnnotationsFilter({
            annotation_label_ids: ['a'],
            collection_ids: ['c1']
        });
        expect(result).toEqual({
            annotation_label_ids: ['a'],
            collection_ids: ['c1'],
            filter_type: 'annotations'
        });
    });

    it('returns undefined when both are empty arrays', () => {
        const result = getAnnotationsFilter({ annotation_label_ids: [], collection_ids: [] });
        expect(result).toBeUndefined();
    });

    it('returns undefined when both are absent', () => {
        const result = getAnnotationsFilter({});
        expect(result).toBeUndefined();
    });
});
