import { describe, expect, it } from 'vitest';
import {
    selectHistogramRange,
    toCategoryCounts,
    toggleCategoricalValue,
    withoutCategoricalValues
} from './distributionHandlers';

describe('toCategoryCounts', () => {
    it('maps current counts, marks selected labels, and drops empty classes', () => {
        const counts = [
            { label_name: 'cat', current_count: 3, total_count: 5 },
            { label_name: 'dog', current_count: 0, total_count: 2 },
            { label_name: 'car', current_count: 1, total_count: 1 }
        ];

        expect(toCategoryCounts(counts, ['car'])).toEqual([
            { label: 'cat', count: 3, selected: false },
            { label: 'car', count: 1, selected: true }
        ]);
    });

    it('returns no bars while the counts are loading', () => {
        expect(toCategoryCounts(undefined, [])).toEqual([]);
    });
});

describe('selectHistogramRange', () => {
    const bound = { min: 0, max: 10 };

    it('clamps the selected range to the bound', () => {
        expect(
            selectHistogramRange({ bound, current: undefined, range: { min: -2, max: 4 } })
        ).toEqual({ min: 0, max: 4 });
    });

    it('resets to the bound when the current range is selected again', () => {
        expect(
            selectHistogramRange({ bound, current: { min: 0, max: 4 }, range: { min: -2, max: 4 } })
        ).toEqual(bound);
    });
});

describe('toggleCategoricalValue', () => {
    it('adds a value that is not selected', () => {
        expect(toggleCategoricalValue(['a'], 'b')).toEqual(['a', 'b']);
    });

    it('removes a selected value, including null for Missing', () => {
        expect(toggleCategoricalValue(['a', null, false], null)).toEqual(['a', false]);
    });
});

describe('withoutCategoricalValues', () => {
    it('removes one key and leaves the input unchanged', () => {
        const values = { city: ['Zurich'], weather: ['sunny'] };

        expect(withoutCategoricalValues(values, 'city')).toEqual({ weather: ['sunny'] });
        expect(values).toEqual({ city: ['Zurich'], weather: ['sunny'] });
    });
});
