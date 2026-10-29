import { describe, expect, it } from 'vitest';
import { matchesSearch, selectAllVisible, type FilterListItem } from './filterList.helpers';

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
