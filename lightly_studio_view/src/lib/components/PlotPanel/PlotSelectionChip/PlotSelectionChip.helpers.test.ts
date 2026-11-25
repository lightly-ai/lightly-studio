import { describe, expect, it } from 'vitest';
import { getPickHint } from './PlotSelectionChip.helpers';

describe('getPickHint', () => {
    it.each([
        { hoveredSampleId: null, pickedSampleIds: ['a'], expected: null },
        { hoveredSampleId: 'a', pickedSampleIds: [], expected: 'pick' },
        { hoveredSampleId: 'b', pickedSampleIds: ['a'], expected: 'add' },
        { hoveredSampleId: 'a', pickedSampleIds: ['a'], expected: 'remove' }
    ])('returns $expected for $hoveredSampleId over $pickedSampleIds', (params) => {
        const { expected, ...hintParams } = params;
        expect(getPickHint(hintParams)).toBe(expected);
    });
});
