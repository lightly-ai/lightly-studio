import { describe, expect, it } from 'vitest';
import type { FilterOption } from './buildOptions';
import { getCheckboxLabel } from './getCheckboxLabel';

const valueOption = (v: string, count = 5): FilterOption => ({
    bucket: { id: v, kind: 'value', value: v, label: v, count },
    retained: false
});
const missingOption = (count = 3): FilterOption => ({
    bucket: { id: 'missing', kind: 'missing', value: null, label: 'Missing', count },
    retained: false
});

describe('getCheckboxLabel', () => {
    it('uses "Select missing metadata" for missing kind', () => {
        expect(getCheckboxLabel(missingOption(3), 'Missing')).toBe(
            'Select missing metadata, 3 samples'
        );
    });

    it('uses "Select value LABEL" for value kind', () => {
        expect(getCheckboxLabel(valueOption('Foo', 5), 'Foo')).toBe('Select value Foo, 5 samples');
    });

    it('uses the label argument, not bucket.label, for the display text', () => {
        const option: FilterOption = {
            bucket: { id: 'a', kind: 'value', value: 'Missing', label: 'Missing', count: 2 },
            retained: false
        };
        expect(getCheckboxLabel(option, 'Missing (value)')).toBe(
            'Select value Missing (value), 2 samples'
        );
    });

    it('shows "count unavailable" for retained options', () => {
        const option: FilterOption = { ...valueOption('stale', 0), retained: true };
        expect(getCheckboxLabel(option, 'stale')).toBe('Select value stale, count unavailable');
    });
});
