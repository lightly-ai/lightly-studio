import { describe, expect, it } from 'vitest';
import type { CategoricalMetadataBucket } from '$lib/hooks/useCategoricalMetadataDistribution/types';
import { buildOptions } from './buildOptions';
import { getSelectionSummary } from './getSelectionSummary';

const buckets: CategoricalMetadataBucket[] = [
    { id: 'a', kind: 'value', value: 'a', label: 'a', count: 1 },
    { id: 'b', kind: 'value', value: 'b', label: 'b', count: 1 }
];
const summary = (selected: string[]) =>
    getSelectionSummary(selected, buildOptions(buckets, selected), buckets);

describe('getSelectionSummary', () => {
    it('describes no, one and several selected values', () => {
        expect(summary([])).toBe('All values');
        expect(summary(['a'])).toBe('a');
        expect(summary(['a', 'b'])).toBe('2 selected');
    });
});
