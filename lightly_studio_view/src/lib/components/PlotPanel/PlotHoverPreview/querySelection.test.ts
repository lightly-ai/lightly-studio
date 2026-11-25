import { describe, expect, it } from 'vitest';

import { createQuerySelection } from './querySelection';
import { INCLUDED_BY_FILTERS_CATEGORY } from '../plotCategories';

describe('createQuerySelection', () => {
    const params = {
        x: new Float32Array([0, 10]),
        y: new Float32Array([0, 10]),
        sampleIds: ['sample-a', 'sample-b'],
        category: new Uint8Array([INCLUDED_BY_FILTERS_CATEGORY, INCLUDED_BY_FILTERS_CATEGORY]),
        isSelectable: () => true
    };

    it('returns the nearest point with its sample ID as identifier', async () => {
        const query = createQuerySelection(params);
        await expect(query(9, 9, 0.5)).resolves.toEqual({
            x: 10,
            y: 10,
            category: INCLUDED_BY_FILTERS_CATEGORY,
            identifier: 'sample-b'
        });
    });

    it('returns null beyond the hover radius, for unselectable points, and without data', async () => {
        const query = createQuerySelection(params);
        await expect(query(5, 5, 0.1)).resolves.toBeNull();

        const unselectableQuery = createQuerySelection({
            ...params,
            isSelectable: (index) => index !== 0
        });
        await expect(unselectableQuery(0, 0, 0.5)).resolves.toBeNull();

        const emptyQuery = createQuerySelection({ ...params, sampleIds: undefined });
        await expect(emptyQuery(0, 0, 0.5)).resolves.toBeNull();
    });
});
