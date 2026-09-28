import { beforeEach, describe, expect, it, vi } from 'vitest';
import { writable } from 'svelte/store';
import {
    useCategoricalMetadataDistribution,
    useMetadataFilters,
    useNumericMetadataDistribution
} from '$lib/hooks';
import { useVideoMetadataDistributionSource } from './useVideoMetadataDistributionSource.svelte';

vi.mock('$lib/hooks', () => ({
    useCategoricalMetadataDistribution: vi.fn(),
    useMetadataFilters: vi.fn(),
    useNumericMetadataDistribution: vi.fn()
}));

const updateMetadataValues = vi.fn();
const updateCategoricalMetadataValues = vi.fn();
const refetch = vi.fn();

const baseFilter = { filter_type: 'video' as const };
const filter = { filter_type: 'video' as const, width: { min: 1, max: 2 } };
const bucket = { id: 'day', kind: 'value', value: 'day', label: 'day', count: 3 };

const mockQueries = () => {
    // A disabled query never fetches, so it has no data.
    vi.mocked(useNumericMetadataDistribution).mockImplementation(
        (getParams) =>
            ({
                get data() {
                    return getParams().enabled ? { fps: { bins: [] } } : undefined;
                },
                isFetching: false
            }) as unknown as ReturnType<typeof useNumericMetadataDistribution>
    );
    vi.mocked(useCategoricalMetadataDistribution).mockImplementation(
        (getParams) =>
            ({
                get data() {
                    const { enabled, filter: queryFilter } = getParams();
                    if (!enabled) return undefined;
                    return { weather: [{ ...bucket, count: queryFilter === filter ? 1 : 3 }] };
                },
                isFetching: false,
                error: null,
                refetch
            }) as unknown as ReturnType<typeof useCategoricalMetadataDistribution>
    );
};

const defaultParams = {
    collectionId: 'collection-1',
    filter,
    baseFilter,
    histogramBinCount: 10,
    activeSourceId: 'metadata' as string | undefined,
    activeGroupId: 'weather' as string | undefined
};

const renderHook = (params: Partial<typeof defaultParams> = {}) =>
    useVideoMetadataDistributionSource(() => ({ ...defaultParams, ...params }));

const groupById = (hook: ReturnType<typeof renderHook>, id: string) =>
    hook.source?.groups?.find((group) => group.id === id);

describe('useVideoMetadataDistributionSource', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(useMetadataFilters).mockReturnValue({
            metadataValues: writable({ fps: { min: 0, max: 60 } }),
            metadataBounds: writable({ fps: { min: 0, max: 60 } }),
            metadataInfo: writable([
                { name: 'fps', type: 'float' },
                { name: 'weather', type: 'string' }
            ]),
            categoricalMetadataValues: writable({ weather: ['day'] }),
            updateMetadataValues,
            updateCategoricalMetadataValues
        } as unknown as ReturnType<typeof useMetadataFilters>);
        mockQueries();
    });

    it('fetches the shown categorical key with the base and the full filter', () => {
        const hook = renderHook();

        expect(groupById(hook, 'weather')?.categorical).toMatchObject({
            buckets: [{ count: 3 }],
            filteredBuckets: [{ count: 1 }],
            selectedValues: ['day']
        });
        expect(groupById(hook, 'fps')?.histogram).toBeUndefined();
    });

    it('fetches the shown numeric key only', () => {
        const hook = renderHook({ activeGroupId: 'fps' });

        expect(groupById(hook, 'fps')?.histogram).toEqual({ bins: [] });
        expect(groupById(hook, 'weather')?.categorical?.buckets).toEqual([]);
    });

    it('fetches nothing while another source is shown', () => {
        const hook = renderHook({ activeSourceId: 'classes' });

        expect(groupById(hook, 'fps')?.histogram).toBeUndefined();
        expect(groupById(hook, 'weather')?.categorical?.buckets).toEqual([]);
    });

    it('turns bar clicks into metadata filters', () => {
        const hook = renderHook();

        hook.onHistogramRangeSelect('fps', { min: 10, max: 20 });
        hook.onCategoricalValueToggle('weather', 'night');
        hook.onCategoricalValuesClear('weather');
        hook.onCategoricalRetry();

        expect(updateMetadataValues).toHaveBeenCalledWith({ fps: { min: 10, max: 20 } });
        expect(updateCategoricalMetadataValues).toHaveBeenNthCalledWith(1, {
            weather: ['day', 'night']
        });
        expect(updateCategoricalMetadataValues).toHaveBeenNthCalledWith(2, {});
        expect(refetch).toHaveBeenCalledTimes(2);
    });
});
