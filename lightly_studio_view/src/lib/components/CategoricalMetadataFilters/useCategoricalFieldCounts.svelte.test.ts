import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { MetadataValueCountsFilter } from '$lib/hooks';
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
    beforeEach(() => vi.resetAllMocks());

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

    const bucket = (id: string, count: number) => ({ id, kind: 'value', value: id, count });

    it('lists values outside the filter with a count of 0', () => {
        queryMock
            .mockReturnValueOnce({ data: { split: [bucket('train', 3)] }, isFetching: false })
            .mockReturnValueOnce({
                data: { split: [bucket('train', 9), bucket('val', 4)] },
                isFetching: false
            });
        const filter: MetadataValueCountsFilter = { filter_type: 'image', width: { min: 100 } };
        const counts = useCategoricalFieldCounts(() => ({
            collectionId,
            filter,
            fields: ['split']
        }));

        expect(counts.distributions.split).toEqual([bucket('train', 3), bucket('val', 0)]);
        expect(queryMock.mock.calls[0][0]().filter).toBe(filter);
        expect(queryMock.mock.calls[1][0]().filter).toEqual({ filter_type: 'image' });
    });

    it('keeps listing all values when the filtered request has no data', () => {
        // Only the request with the width restriction fails.
        queryMock.mockImplementation((getOptions: () => DistributionOptions) =>
            getOptions().filter?.width
                ? { data: undefined, isFetching: false, error: new Error('down') }
                : { data: { split: [bucket('val', 4)] }, isFetching: false }
        );
        const counts = useCategoricalFieldCounts(() => ({
            collectionId,
            filter: { filter_type: 'image', width: { min: 100 } },
            fields: ['split']
        }));

        expect(counts.distributions.split).toEqual([bucket('val', 0)]);
        expect(counts.error).toBe('down');
    });

    it('reports all values loaded only after the all-values request has data', () => {
        const filter: MetadataValueCountsFilter = { filter_type: 'image', width: { min: 100 } };
        queryMock.mockReturnValue({ data: undefined, isFetching: true });
        const pending = useCategoricalFieldCounts(() => ({ collectionId, filter, fields: ['a'] }));
        expect(pending.allValuesLoaded).toBe(false);

        queryMock.mockReturnValue({ data: { a: [] }, isFetching: false });
        const loaded = useCategoricalFieldCounts(() => ({ collectionId, filter, fields: ['a'] }));
        expect(loaded.allValuesLoaded).toBe(true);

        const unfiltered = useCategoricalFieldCounts(() => ({ collectionId, fields: ['a'] }));
        expect(unfiltered.allValuesLoaded).toBe(true);
    });

    it('skips the all-values request without a filter', () => {
        captureOptions(['split']);
        expect(queryMock.mock.calls[1][0]().enabled).toBe(false);
    });
});
