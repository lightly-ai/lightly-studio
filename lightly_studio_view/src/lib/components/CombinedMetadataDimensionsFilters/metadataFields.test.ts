import { expect, it } from 'vitest';
import type { CategoricalMetadataValue } from '$lib/services/types';
import { formatFloat } from '$lib/utils';
import {
    fieldId,
    formatRangeSummary,
    isFieldActive,
    orderByActive,
    type CategoricalField,
    type RangeField
} from './metadataFields';

const range = (over: Partial<RangeField> = {}): RangeField => ({
    kind: 'range',
    id: fieldId('numeric', 'score'),
    source: 'numeric',
    key: 'score',
    title: 'score',
    unit: '',
    bound: { min: 0, max: 1 },
    value: { min: 0, max: 1 },
    ...over
});
const categorical = (selected: CategoricalMetadataValue[]): CategoricalField => ({
    kind: 'categorical',
    id: fieldId('categorical', 'split'),
    source: 'categorical',
    key: 'split',
    title: 'split',
    selected
});

it('a range at its bounds is not active', () => expect(isFieldActive(range())).toBe(false));
it('a narrowed range is active', () =>
    expect(isFieldActive(range({ value: { min: 0.2, max: 1 } }))).toBe(true));
it('a field with equal bounds is never active', () =>
    expect(isFieldActive(range({ bound: { min: 5, max: 5 }, value: { min: 5, max: 5 } }))).toBe(
        false
    ));
it('a categorical field with selected values is active', () => {
    expect(isFieldActive(categorical([]))).toBe(false);
    expect(isFieldActive(categorical([null]))).toBe(true);
});
it('orders active fields first and keeps the order inside each group', () => {
    const a = range({ id: 'numeric:a', key: 'a' });
    const b = range({ id: 'numeric:b', key: 'b', value: { min: 0.5, max: 1 } });
    const c = categorical(['train']);
    expect(orderByActive([a, b, c])).toEqual({ fields: [b, c, a], activeCount: 2 });
});
it('ids differ for a metadata key named width', () =>
    expect(fieldId('dimension', 'width')).not.toBe(fieldId('numeric', 'width')));
it('formats integer ranges with the unit', () =>
    expect(
        formatRangeSummary(
            range({ unit: 'px', bound: { min: 0, max: 1024 }, value: { min: 200, max: 640 } })
        )
    ).toBe('200px – 640px'));
it('formats float ranges like the slider labels', () =>
    expect(formatRangeSummary(range({ value: { min: 0.25, max: 0.5 } }))).toBe(
        `${formatFloat(0.25)} – ${formatFloat(0.5)}`
    ));
