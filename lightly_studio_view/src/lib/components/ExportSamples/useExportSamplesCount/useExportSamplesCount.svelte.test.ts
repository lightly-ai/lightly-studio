import { render } from '@testing-library/svelte';
import { get } from 'svelte/store';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { flushSync } from 'svelte';
import { waitFor } from '@testing-library/svelte';
import UseExportSamplesCountHarness from './UseExportSamplesCountHarness.svelte';
import type { useExportSamplesCount } from './useExportSamplesCount.svelte';
import type { ImageFilter } from '$lib/api/lightly_studio_local';

const { exportCollectionStats } = vi.hoisted(() => ({
    exportCollectionStats: vi.fn()
}));

vi.mock('$lib/api/lightly_studio_local', () => ({
    exportCollectionStats
}));

type HookResult = ReturnType<typeof useExportSamplesCount>;

const renderHook = (props: {
    collectionId: string;
    collectionFilter?: ImageFilter | null;
}): HookResult => {
    let result: HookResult | undefined;
    render(UseExportSamplesCountHarness, {
        ...props,
        onReady: (r: HookResult) => {
            result = r;
        }
    });
    flushSync();
    if (!result) throw new Error('UseExportSamplesCountHarness did not initialize');
    return result;
};

const filterA: ImageFilter = { filter_type: 'image', sample_filter: { sample_ids: ['id-1'] } };
const filterB: ImageFilter = { filter_type: 'image', sample_filter: { sample_ids: ['id-2'] } };

describe('useExportSamplesCount', () => {
    beforeEach(() => {
        vi.resetAllMocks();
    });

    it('makes the correct API call with collectionFilter', async () => {
        exportCollectionStats.mockResolvedValue({ data: 10 });

        renderHook({ collectionId: 'col-1', collectionFilter: filterA });

        await waitFor(() => {
            expect(exportCollectionStats).toHaveBeenCalledWith(
                expect.objectContaining({
                    path: { collection_id: 'col-1' },
                    body: { collection_filter: filterA }
                })
            );
        });
    });

    it('does not call the API when collectionFilter is absent', () => {
        renderHook({ collectionId: 'col-1' });

        expect(exportCollectionStats).not.toHaveBeenCalled();
    });

    it('transitions isLoading: false → true → false as request settles', async () => {
        let resolveStats!: (value: { data: number }) => void;
        exportCollectionStats.mockReturnValue(
            new Promise<{ data: number }>((resolve) => {
                resolveStats = resolve;
            })
        );

        const { isLoading } = renderHook({ collectionId: 'col-1', collectionFilter: filterA });

        await waitFor(() => expect(get(isLoading)).toBe(true));

        resolveStats({ data: 3 });

        await waitFor(() => expect(get(isLoading)).toBe(false));
    });

    it('sets error when the API call rejects', async () => {
        exportCollectionStats.mockRejectedValue(new Error('network error'));

        const { error } = renderHook({ collectionId: 'col-1', collectionFilter: filterA });

        await waitFor(() => expect(get(error)).toBe('network error'));
    });

    it('writes count of zero to the store (not silently dropped)', async () => {
        exportCollectionStats.mockResolvedValue({ data: 5 });

        let hookResult: HookResult | undefined;
        const { rerender } = render(UseExportSamplesCountHarness, {
            collectionId: 'col-1',
            collectionFilter: filterA,
            onReady: (r: HookResult) => {
                hookResult = r;
            }
        });
        flushSync();
        if (!hookResult) throw new Error('UseExportSamplesCountHarness did not initialize');
        const { count } = hookResult;

        await waitFor(() => expect(get(count)).toBe(5));

        exportCollectionStats.mockResolvedValue({ data: 0 });
        await rerender({
            collectionId: 'col-1',
            collectionFilter: filterB,
            onReady: (r: HookResult) => {
                hookResult = r;
            }
        });

        await waitFor(() => expect(get(count)).toBe(0));
    });
});
