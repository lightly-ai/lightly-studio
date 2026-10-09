import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getMetadataValueCountsQueryKey } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { getMetadataValueCounts } from '$lib/api/lightly_studio_local/sdk.gen';
import type { MetadataValueCountsView } from '$lib/api/lightly_studio_local';
import {
    getCategoricalMetadataDistributionRequestOptions,
    selectCategoricalDistributions,
    useCategoricalMetadataDistribution
} from './useCategoricalMetadataDistribution.svelte';

describe('selectCategoricalDistributions', () => {
    it('maps concrete value counts to labelled value buckets', () => {
        const response: Record<string, MetadataValueCountsView> = {
            city: {
                value_counts: [
                    { value: 'Zurich', count: 10 },
                    { value: true, count: 2 }
                ]
            }
        };

        expect(selectCategoricalDistributions(response).city).toEqual([
            {
                id: '["value","string","Zurich"]',
                kind: 'value',
                value: 'Zurich',
                label: 'Zurich',
                count: 10
            },
            { id: '["value","boolean",true]', kind: 'value', value: true, label: 'true', count: 2 }
        ]);
    });

    it('maps __missing__ sentinel to a missing bucket', () => {
        const response: Record<string, MetadataValueCountsView> = {
            city: { value_counts: [{ value: '__missing__', count: 3 }] }
        };

        expect(selectCategoricalDistributions(response).city).toEqual([
            { id: '["missing"]', kind: 'missing', value: null, label: 'Missing', count: 3 }
        ]);
    });

    it('maps __other__ sentinel to an other bucket', () => {
        const response: Record<string, MetadataValueCountsView> = {
            city: { value_counts: [{ value: '__other__', count: 5 }] }
        };

        expect(selectCategoricalDistributions(response).city).toEqual([
            { id: '["other"]', kind: 'other', label: 'Other', count: 5 }
        ]);
    });

    it('disambiguates literal "Missing" and "Other" values when sentinels are also present', () => {
        const response: Record<string, MetadataValueCountsView> = {
            city: {
                value_counts: [
                    { value: 'Missing', count: 4 },
                    { value: 'Other', count: 1 },
                    { value: '__missing__', count: 3 },
                    { value: '__other__', count: 7 }
                ]
            }
        };

        expect(selectCategoricalDistributions(response).city).toEqual([
            {
                id: '["value","string","Missing"]',
                kind: 'value',
                value: 'Missing',
                label: 'Missing (value)',
                count: 4
            },
            {
                id: '["value","string","Other"]',
                kind: 'value',
                value: 'Other',
                label: 'Other (value)',
                count: 1
            },
            {
                id: '["missing"]',
                kind: 'missing',
                value: null,
                label: 'Missing (no value)',
                count: 3
            },
            { id: '["other"]', kind: 'other', label: 'Other (aggregated)', count: 7 }
        ]);
    });

    it('maps an empty value_counts to an empty array and an absent response to an empty record', () => {
        expect(selectCategoricalDistributions({ city: { value_counts: [] } })).toEqual({
            city: []
        });
        expect(selectCategoricalDistributions(undefined)).toEqual({});
    });
});

describe('getCategoricalMetadataDistributionRequestOptions', () => {
    it('forwards the active image filter', () => {
        expect(
            getCategoricalMetadataDistributionRequestOptions({
                collectionId: 'collection-id',
                filter: { filter_type: 'image', width: { min: 100 } }
            })
        ).toEqual({
            path: { collection_id: 'collection-id' },
            body: { limit: null, filters: { filter_type: 'image', width: { min: 100 } } }
        });
    });
});

describe('categorical field selection', () => {
    it('preserves selected fields and filters, including an empty field selection', () => {
        for (const fields of [['city'], ['city', 'weather'], []]) {
            for (const filter of [
                undefined,
                { filter_type: 'image' as const, width: { min: 100 } }
            ]) {
                expect(
                    getCategoricalMetadataDistributionRequestOptions({
                        collectionId: 'collection-id',
                        fields,
                        filter
                    })
                ).toEqual({
                    path: { collection_id: 'collection-id' },
                    body: { limit: null, fields, ...(filter ? { filters: filter } : {}) }
                });
            }
        }
    });

    it('uses separate cache entries when the selected field changes', () => {
        const keys = ['city', 'weather'].map((field) =>
            getMetadataValueCountsQueryKey(
                getCategoricalMetadataDistributionRequestOptions({
                    collectionId: 'collection-id',
                    fields: [field]
                })
            )
        );
        expect(keys[0]).not.toEqual(keys[1]);
    });
});

interface QueryOptions {
    enabled: boolean;
    queryFn: (context: { signal: AbortSignal }) => Promise<unknown>;
    placeholderData: (previous: Record<string, MetadataValueCountsView> | undefined) => unknown;
    select: typeof selectCategoricalDistributions;
}

const createQueryMock = vi.hoisted(() => vi.fn<(getOptions: () => QueryOptions) => unknown>());

vi.mock('@tanstack/svelte-query', async (importOriginal) => ({
    ...(await importOriginal<typeof import('@tanstack/svelte-query')>()),
    createQuery: createQueryMock
}));
vi.mock('$lib/api/lightly_studio_local/sdk.gen', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/api/lightly_studio_local/sdk.gen')>()),
    getMetadataValueCounts: vi.fn()
}));

describe('useCategoricalMetadataDistribution', () => {
    beforeEach(() => vi.clearAllMocks());

    it('fetches the selected field with filters and cancellation, and keeps previous bars while loading', async () => {
        const data = { city: { value_counts: [{ value: 'Zurich', count: 4 }] } };
        vi.mocked(getMetadataValueCounts).mockResolvedValue({
            data,
            request: new Request('http://localhost/metadata/value-counts'),
            response: new Response()
        });
        useCategoricalMetadataDistribution(() => ({
            collectionId: 'collection-id',
            fields: ['city'],
            filter: { filter_type: 'image', width: { min: 100 } }
        }));
        const options = createQueryMock.mock.calls[0][0]();
        const signal = new AbortController().signal;

        expect(options.enabled).toBe(true);
        await expect(options.queryFn({ signal })).resolves.toEqual(data);
        expect(getMetadataValueCounts).toHaveBeenCalledWith({
            path: { collection_id: 'collection-id' },
            body: {
                limit: null,
                fields: ['city'],
                filters: { filter_type: 'image', width: { min: 100 } }
            },
            signal,
            throwOnError: true
        });
        expect(options.select(data).city).toEqual([
            {
                id: '["value","string","Zurich"]',
                kind: 'value',
                value: 'Zurich',
                label: 'Zurich',
                count: 4
            }
        ]);
        expect(options.placeholderData(data)).toBe(data);
        expect(options.placeholderData(undefined)).toBeUndefined();
    });

    it('respects disabled queries and propagates request errors', async () => {
        useCategoricalMetadataDistribution(() => ({
            collectionId: 'collection-id',
            enabled: false
        }));
        const options = createQueryMock.mock.calls[0][0]();
        expect(options.enabled).toBe(false);
        const error = new Error('Request failed');
        vi.mocked(getMetadataValueCounts).mockRejectedValue(error);
        await expect(options.queryFn({ signal: new AbortController().signal })).rejects.toBe(error);
    });
});
