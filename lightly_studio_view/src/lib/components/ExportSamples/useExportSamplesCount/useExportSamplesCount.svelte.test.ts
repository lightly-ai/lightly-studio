import { render } from '@testing-library/svelte';
import { get } from 'svelte/store';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { flushSync } from 'svelte';
import { waitFor } from '@testing-library/svelte';
import UseExportSamplesCountHarness from './UseExportSamplesCountHarness.svelte';
import type { useExportSamplesCount } from './useExportSamplesCount.svelte';

const { exportCollectionStats } = vi.hoisted(() => ({
    exportCollectionStats: vi.fn()
}));

vi.mock('$lib/api/lightly_studio_local', () => ({
    exportCollectionStats
}));

type HookResult = ReturnType<typeof useExportSamplesCount>;

const renderHook = (props: {
    collectionId: string;
    includeFilter?: Record<string, unknown>;
    excludeFilter?: Record<string, unknown>;
    collectionFilter?: Record<string, unknown> | null;
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

describe('useExportSamplesCount', () => {
    beforeEach(() => {
        vi.resetAllMocks();
    });

    it('makes the correct API call with includeFilter', async () => {
        exportCollectionStats.mockResolvedValue({ data: 10 });

        renderHook({
            collectionId: 'col-1',
            includeFilter: { tag_ids: ['tag-1'] }
        });

        await waitFor(() => {
            expect(exportCollectionStats).toHaveBeenCalledWith(
                expect.objectContaining({
                    path: { collection_id: 'col-1' },
                    body: {
                        include: { tag_ids: ['tag-1'] },
                        exclude: undefined,
                        collection_filter: undefined
                    }
                })
            );
        });
    });

    it('transitions isLoading: false → true → false as request settles', async () => {
        let resolveStats!: (value: { data: number }) => void;
        exportCollectionStats.mockReturnValue(
            new Promise<{ data: number }>((resolve) => {
                resolveStats = resolve;
            })
        );

        const { isLoading } = renderHook({
            collectionId: 'col-1',
            includeFilter: { tag_ids: ['tag-1'] }
        });

        await waitFor(() => expect(get(isLoading)).toBe(true));

        resolveStats({ data: 3 });

        await waitFor(() => expect(get(isLoading)).toBe(false));
    });

    it('sets error when the API call rejects', async () => {
        exportCollectionStats.mockRejectedValue(new Error('network error'));

        const { error } = renderHook({
            collectionId: 'col-1',
            includeFilter: { tag_ids: ['tag-1'] }
        });

        await waitFor(() => expect(get(error)).toBe('network error'));
    });

    it('writes count of zero to the store (not silently dropped)', async () => {
        exportCollectionStats.mockResolvedValue({ data: 5 });

        let hookResult: HookResult | undefined;
        const { rerender } = render(UseExportSamplesCountHarness, {
            collectionId: 'col-1',
            includeFilter: { tag_ids: ['tag-1'] },
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
            includeFilter: { tag_ids: ['tag-1', 'tag-2'] },
            onReady: (r: HookResult) => {
                hookResult = r;
            }
        });

        await waitFor(() => expect(get(count)).toBe(0));
    });

    it('calls the API with both collectionFilter and includeFilter', async () => {
        exportCollectionStats.mockResolvedValue({ data: 7 });
        const collectionFilter = { score: { min: 0.5, max: 1.0 } };

        const { count } = renderHook({
            collectionId: 'col-1',
            includeFilter: { tag_ids: ['tag-2'] },
            collectionFilter
        });

        await waitFor(() => {
            expect(exportCollectionStats).toHaveBeenCalledWith(
                expect.objectContaining({
                    body: {
                        include: { tag_ids: ['tag-2'] },
                        exclude: undefined,
                        collection_filter: collectionFilter
                    }
                })
            );
        });
        await waitFor(() => expect(get(count)).toBe(7));
    });

    it('calls the API with collectionFilter only', async () => {
        exportCollectionStats.mockResolvedValue({ data: 4 });
        const collectionFilter = { score: { min: 0.8, max: 1.0 } };

        const { count } = renderHook({
            collectionId: 'col-1',
            collectionFilter
        });

        await waitFor(() => {
            expect(exportCollectionStats).toHaveBeenCalledWith(
                expect.objectContaining({
                    body: {
                        include: undefined,
                        exclude: undefined,
                        collection_filter: collectionFilter
                    }
                })
            );
        });
        await waitFor(() => expect(get(count)).toBe(4));
    });
});
