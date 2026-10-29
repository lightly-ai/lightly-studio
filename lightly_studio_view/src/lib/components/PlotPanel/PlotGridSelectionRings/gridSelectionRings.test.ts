import { describe, expect, it } from 'vitest';
import { MAX_GRID_SELECTION_RINGS, getGridSelectionPointIndices } from './gridSelectionRings';

describe('getGridSelectionPointIndices', () => {
    const sampleIndexById = new Map([
        ['a', 0],
        ['b', 1],
        ['c', 2]
    ]);

    it('returns the points of the selected samples, skipping missing and hidden ones', () => {
        // 0 hidden, 2 included.
        const category = new Uint8Array([2, 0, 2]);

        const indices = getGridSelectionPointIndices(
            new Set(['a', 'b', 'c', 'not-in-plot']),
            sampleIndexById,
            category
        );

        expect(indices).toEqual([0, 2]);
    });

    it('caps the number of rings', () => {
        const count = MAX_GRID_SELECTION_RINGS + 10;
        const sampleIds = Array.from({ length: count }, (_, index) => `sample-${index}`);
        const manyIndexById = new Map(sampleIds.map((sampleId, index) => [sampleId, index]));

        const indices = getGridSelectionPointIndices(new Set(sampleIds), manyIndexById, undefined);

        expect(indices).toHaveLength(MAX_GRID_SELECTION_RINGS);
    });
});
