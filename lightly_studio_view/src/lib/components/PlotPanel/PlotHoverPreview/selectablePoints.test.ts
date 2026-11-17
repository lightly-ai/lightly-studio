import { describe, expect, it } from 'vitest';
import { createSelectablePointCheck } from './selectablePoints';
import {
    EXCLUDED_BY_FILTERS_CATEGORY,
    HIDDEN_CATEGORY,
    INCLUDED_BY_FILTERS_CATEGORY
} from '../plotCategories';

describe('createSelectablePointCheck', () => {
    const category = new Uint8Array([
        INCLUDED_BY_FILTERS_CATEGORY,
        EXCLUDED_BY_FILTERS_CATEGORY,
        HIDDEN_CATEGORY
    ]);
    const sampleIds = ['sample-a', 'sample-b', 'sample-c'];

    it('excludes greyed-out and hidden points without an active filter', () => {
        const isSelectable = createSelectablePointCheck({
            category,
            sampleIds,
            fulfilsFilter: undefined,
            pickedSampleIds: []
        });
        expect([0, 1, 2].map(isSelectable)).toEqual([true, false, false]);
    });

    it('keeps a greyed-out point that passes the filters selectable', () => {
        const isSelectable = createSelectablePointCheck({
            category,
            sampleIds,
            fulfilsFilter: new Uint8Array([1, 1, 1]),
            pickedSampleIds: []
        });
        expect([0, 1, 2].map(isSelectable)).toEqual([true, true, false]);
    });

    it('keeps a picked point selectable when it fails the filters', () => {
        const isSelectable = createSelectablePointCheck({
            category,
            sampleIds,
            fulfilsFilter: new Uint8Array([1, 0, 0]),
            pickedSampleIds: ['sample-b']
        });
        expect([0, 1, 2].map(isSelectable)).toEqual([true, true, false]);
    });
});
