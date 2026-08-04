import { describe, expect, it } from 'vitest';
import type { CategoricalBucket } from '../../types';
import type { FilterOption } from './buildOptions';
import { getOptionLabel } from './getOptionLabel';

const valueOption = (v: string, label = v): FilterOption => ({
    bucket: { id: v, kind: 'value', value: v, label, count: 1 },
    retained: false
});
const missingOption = (): FilterOption => ({
    bucket: { id: 'missing', kind: 'missing', value: null, label: 'Missing', count: 1 },
    retained: false
});
const otherBucket = (): CategoricalBucket => ({
    id: 'other',
    kind: 'other',
    label: 'Other',
    count: 5
});

describe('getOptionLabel', () => {
    it('returns bucket label for a regular value', () => {
        const option = valueOption('foo', 'Foo');
        expect(getOptionLabel(option, [option], [])).toBe('Foo');
    });

    it('disambiguates missing bucket when a literal "Missing" value is also present', () => {
        const absent = missingOption();
        const literal = valueOption('Missing');
        expect(getOptionLabel(absent, [absent, literal], [])).toBe('Missing (no value)');
    });

    it('disambiguates literal "Missing" value when a missing bucket is present', () => {
        const absent = missingOption();
        const literal = valueOption('Missing');
        expect(getOptionLabel(literal, [absent, literal], [])).toBe('Missing (value)');
    });

    it('leaves "Missing" label unchanged when no missing bucket is present', () => {
        const literal = valueOption('Missing');
        expect(getOptionLabel(literal, [literal], [])).toBe('Missing');
    });

    it('disambiguates literal "Other" value when an other aggregate bucket is present', () => {
        const option = valueOption('Other');
        expect(getOptionLabel(option, [option], [otherBucket()])).toBe('Other (value)');
    });

    it('leaves "Other" label unchanged when no other aggregate bucket is present', () => {
        const option = valueOption('Other');
        expect(getOptionLabel(option, [option], [])).toBe('Other');
    });
});
