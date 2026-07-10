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
        const visible = selectVisibleCounts(data, {
            mode: 'topN',
            n: 3,
            sortBy: 'count',
            manualClasses: []
        });
        expect(visible.map((item) => item.label)).toEqual(['person', 'dog', 'bike']);
    });

    it('ranks by name ascending', () => {
        const visible = selectVisibleCounts(data, {
            mode: 'topN',
            n: 4,
            sortBy: 'name',
            manualClasses: []
        });
        expect(visible.map((item) => item.label)).toEqual(['bike', 'car', 'dog', 'person']);
    });

    it('clamps n to at least one visible class', () => {
        const visible = selectVisibleCounts(data, {
            mode: 'topN',
            n: 0,
            sortBy: 'count',
            manualClasses: []
        });
        expect(visible.map((item) => item.label)).toEqual(['person']);
    });

    it('keeps only the manually selected classes, ignoring n', () => {
        const visible = selectVisibleCounts(data, {
            mode: 'manual',
            n: 1,
            sortBy: 'count',
            manualClasses: ['car', 'dog']
        });
        expect(visible.map((item) => item.label)).toEqual(['dog', 'car']);
    });

    it('returns nothing when the manual selection is empty', () => {
        const visible = selectVisibleCounts(data, {
            mode: 'manual',
            n: 3,
            sortBy: 'count',
            manualClasses: []
        });
        expect(visible).toEqual([]);
    });
});
