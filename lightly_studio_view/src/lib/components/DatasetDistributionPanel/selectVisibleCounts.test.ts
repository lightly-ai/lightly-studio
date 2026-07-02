import { describe, expect, it } from 'vitest';
import { selectVisibleCounts } from './selectVisibleCounts';

const data = [
    { label: 'car', count: 3 },
    { label: 'person', count: 10 },
    { label: 'bike', count: 3 },
    { label: 'dog', count: 7 }
];

describe('selectVisibleCounts', () => {
    it('ranks by count descending with name tie-break and keeps the top n', () => {
        const visible = selectVisibleCounts(data, { n: 3, sortBy: 'count' });
        expect(visible.map((item) => item.label)).toEqual(['person', 'dog', 'bike']);
    });

    it('ranks by name ascending', () => {
        const visible = selectVisibleCounts(data, { n: 4, sortBy: 'name' });
        expect(visible.map((item) => item.label)).toEqual(['bike', 'car', 'dog', 'person']);
    });

    it('clamps n to at least one visible class', () => {
        const visible = selectVisibleCounts(data, { n: 0, sortBy: 'count' });
        expect(visible.map((item) => item.label)).toEqual(['person']);
    });
});
