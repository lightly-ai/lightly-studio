import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { MetadataJointDistributionView } from '$lib/api/lightly_studio_local';
import { getMetadataJointDistribution } from '$lib/api/lightly_studio_local/sdk.gen';
import {
    getMetadataJointDistributionRequestOptions,
    useMetadataJointDistribution
} from './useMetadataJointDistribution.svelte';

const filterWithMetadata = {
    filter_type: 'image' as const,
    sample_filter: {
        metadata_filters: [
            { key: 'month', op: 'in' as const, value: ['April'] },
            { key: 'year', op: '<=' as const, value: 2025 },
            { key: 'weather', op: 'in' as const, value: ['sunny'] }
        ]
    }
};

describe('getMetadataJointDistributionRequestOptions', () => {
    it('drops the filters of both axis keys and keeps the other filters', () => {
        expect(
            getMetadataJointDistributionRequestOptions({
                collectionId: 'collection-id',
                xKey: 'month',
                yKey: 'year',
                binCount: 10,
                filter: filterWithMetadata
            })
        ).toEqual({
            path: { collection_id: 'collection-id' },
            body: {
                x_key: 'month',
                y_key: 'year',
                bin_count: 10,
                filters: {
                    filter_type: 'image',
                    sample_filter: {
                        metadata_filters: [{ key: 'weather', op: 'in', value: ['sunny'] }]
                    }
                }
            }
        });
    });

    it('omits the filters when there is no filter', () => {
        expect(
            getMetadataJointDistributionRequestOptions({
                collectionId: 'collection-id',
                xKey: 'month',
                yKey: 'year',
                binCount: 20
            }).body
        ).toEqual({ x_key: 'month', y_key: 'year', bin_count: 20 });
    });
});

interface QueryOptions {
    enabled: boolean;
    queryFn: (context: { signal: AbortSignal }) => Promise<unknown>;
    placeholderData: (previous: MetadataJointDistributionView | undefined) => unknown;
}

const createQueryMock = vi.hoisted(() => vi.fn<(getOptions: () => QueryOptions) => unknown>());

vi.mock('@tanstack/svelte-query', async (importOriginal) => ({
    ...(await importOriginal<typeof import('@tanstack/svelte-query')>()),
    createQuery: createQueryMock
}));
vi.mock('$lib/api/lightly_studio_local/sdk.gen', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/api/lightly_studio_local/sdk.gen')>()),
    getMetadataJointDistribution: vi.fn()
}));

const distribution = (xKey: string, yKey: string): MetadataJointDistributionView => ({
    x_axis: { key: xKey, type: 'string', buckets: [{ kind: 'value', value: 'April' }] },
    y_axis: { key: yKey, type: 'integer', buckets: [{ kind: 'range', min: 2025, max: 2025 }] },
    counts: [[3]]
});

describe('useMetadataJointDistribution', () => {
    beforeEach(() => vi.clearAllMocks());

    it('fetches the counts with cancellation', async () => {
        const data = distribution('month', 'year');
        vi.mocked(getMetadataJointDistribution).mockResolvedValue({
            data,
            request: new Request('http://localhost/metadata/joint-distribution'),
            response: new Response()
        });
        useMetadataJointDistribution(() => ({
            collectionId: 'collection-id',
            xKey: 'month',
            yKey: 'year',
            binCount: 10,
            enabled: false
        }));
        const options = createQueryMock.mock.calls[0][0]();
        const signal = new AbortController().signal;

        expect(options.enabled).toBe(false);
        await expect(options.queryFn({ signal })).resolves.toEqual(data);
        expect(getMetadataJointDistribution).toHaveBeenCalledWith({
            path: { collection_id: 'collection-id' },
            body: { x_key: 'month', y_key: 'year', bin_count: 10 },
            signal,
            throwOnError: true
        });
    });

    it('keeps the previous counts only while the axis keys stay the same', () => {
        useMetadataJointDistribution(() => ({
            collectionId: 'collection-id',
            xKey: 'month',
            yKey: 'year',
            binCount: 10
        }));
        const options = createQueryMock.mock.calls[0][0]();

        const sameKeys = distribution('month', 'year');
        expect(options.placeholderData(sameKeys)).toBe(sameKeys);
        expect(options.placeholderData(distribution('month', 'weather'))).toBeUndefined();
        expect(options.placeholderData(undefined)).toBeUndefined();
    });
});
