import { describe, expect, it } from 'vitest';
import {
    highlightRange,
    matchesSearch,
    selectAllVisible,
    splitMatch,
    type FilterListItem
} from './filterList.helpers';

const item = (id: string, selected = false): FilterListItem => ({ id, label: id, selected });

describe('matchesSearch', () => {
    it('ignores case and surrounding spaces', () => {
        expect(matchesSearch(item('Deer'), ' dee ')).toBe(true);
        expect(matchesSearch(item('Deer'), 'fox')).toBe(false);
    });
});

describe('selectAllVisible', () => {
    it('adds the visible items to the selection', () => {
        const items = [item('car', true), item('cat'), item('dog')];
        expect(selectAllVisible(items, [item('cat')])).toEqual(['car', 'cat']);
    });
});

describe('highlightRange', () => {
    it('finds the trimmed search in the label, ignoring case', () => {
        expect(highlightRange('Person', ' ers ')).toEqual({ start: 1, end: 4 });
        expect(highlightRange('Person', 'car')).toBeNull();
        expect(highlightRange('Person', '  ')).toBeNull();
    });
});

describe('splitMatch', () => {
    it('splits around the range, or returns the text unsplit without one', () => {
        expect(splitMatch('person', { start: 0, end: 3 })).toEqual(['', 'per', 'son']);
        expect(splitMatch('person', null)).toEqual(['person', '', '']);
    });
});
