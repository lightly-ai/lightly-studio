import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { MetadataValueCountsFilter } from '$lib/hooks/useCategoricalMetadataDistribution/useCategoricalMetadataDistribution.svelte';
import { useCategoricalFieldCounts } from './useCategoricalFieldCounts.svelte';

const collectionId = '123e4567-e89b-42d3-a456-426614174000';

const queryMock = vi.hoisted(() => vi.fn());
vi.mock('$lib/hooks', () => ({ useCategoricalMetadataDistribution: queryMock }));

type DistributionOptions = {
    collectionId: string;
    filter?: MetadataValueCountsFilter;
    fields: string[];
    enabled: boolean;
};

const captureOptions = (fields: string[], filter?: MetadataValueCountsFilter) => {
    queryMock.mockReturnValue({ data: undefined, isFetching: false, isLoading: false });
    useCategoricalFieldCounts(() => ({ collectionId, filter, fields }));
    return queryMock.mock.calls[0][0]() as DistributionOptions;
};

describe('useCategoricalFieldCounts', () => {
    beforeEach(() => vi.clearAllMocks());

    it('requests only expanded fields with the given filter', () => {
        const filter: MetadataValueCountsFilter = {
            filter_type: 'video',
            width: { min: 100 }
        };
        const options = captureOptions(['split'], filter);

        expect(options.fields).toEqual(['split']);
        expect(options.filter).toBe(filter);
        expect(options.enabled).toBe(true);
    });

    it('does not request when no field is expanded', () => {
        expect(captureOptions([]).enabled).toBe(false);
    });

    it('reports loading and updating from the query state', () => {
        queryMock.mockReturnValue({
            data: { split: [] },
            isFetching: true,
            isLoading: false,
            isPlaceholderData: true
        });
        const counts = useCategoricalFieldCounts(() => ({ collectionId, fields: ['a'] }));

        expect(counts.distributions).toEqual({ split: [] });
        expect(counts.loading).toBe(true);
        expect(counts.updating).toBe(true);
    });
});
