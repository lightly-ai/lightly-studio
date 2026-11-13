import { describe, expect, it } from 'vitest';
import type { CategoricalMetadataBucket } from '$lib/hooks/useCategoricalMetadataDistribution/types';
import { withAllValues } from './withAllValues';

const value = (v: string, count: number): CategoricalMetadataBucket => ({
    id: v,
    kind: 'value',
    value: v,
    label: v,
    count
});

describe('withAllValues', () => {
    it('keeps the filtered counts and appends the other values with a count of 0', () => {
        const result = withAllValues(
            [value('paris', 3)],
            [value('berlin', 5), value('paris', 7), value('rome', 2)]
        );

        expect(result.map(({ id, count }) => [id, count])).toEqual([
            ['paris', 3],
            ['berlin', 0],
            ['rome', 0]
        ]);
    });
});
