import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import type { VideoView } from '$lib/api/lightly_studio_local/types.gen';
import { createQuery, useQueryClient } from '@tanstack/svelte-query';
import { render } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import UseVideoHarness from './UseVideoHarness.svelte';
import type { useVideo } from './useVideo.svelte';

vi.mock('$lib/api/lightly_studio_local/@tanstack/svelte-query.gen', () => ({
    getVideoByIdOptions: vi.fn((config) => ({
        queryKey: ['video', config.path.sample_id],
        ...config
    }))
}));

vi.mock('@tanstack/svelte-query', () => ({
    createQuery: vi.fn(),
    useQueryClient: vi.fn()
}));

describe('useVideo', () => {
    const mockVideoData: VideoView = {
        sample_id: 'video-1',
        file_name: 'test.mp4',
        width: 1920,
        height: 1080,
        duration_s: 10,
        fps: 30
    } as VideoView;

    const mockQueryClient = {
        invalidateQueries: vi.fn()
    };

    const defaultQueryResult = {
        data: undefined as VideoView | undefined,
        error: null as Error | null,
        isLoading: false
    };

    let mockQueryResult = { ...defaultQueryResult };

    const renderHook = () => {
        let result: ReturnType<typeof useVideo> | undefined;

        render(UseVideoHarness, {
            onReady: (hookResult) => {
                result = hookResult;
            }
        });
        flushSync();

        if (!result) {
            throw new Error('useVideo harness did not initialize');
        }

        return result;
    };

    beforeEach(() => {
        vi.clearAllMocks();
        mockQueryResult = { ...defaultQueryResult };
        vi.mocked(createQuery).mockReturnValue(
            mockQueryResult as unknown as ReturnType<typeof createQuery>
        );
        vi.mocked(useQueryClient).mockReturnValue(
            mockQueryClient as unknown as ReturnType<typeof useQueryClient>
        );
    });

    it('should initialize with undefined data, null error, and false isLoading', () => {
        const { data, error, isLoading } = renderHook();

        expect(get(data)).toBeUndefined();
        expect(get(error)).toBeNull();
        expect(get(isLoading)).toBe(false);
    });

    it('should load video data by sample_id', () => {
        mockQueryResult.data = mockVideoData;

        const { data, error, isLoading, loadById } = renderHook();

        flushSync(() => loadById('video-1'));

        expect(createQuery).toHaveBeenCalledWith(expect.any(Function));
        expect(vi.mocked(createQuery).mock.calls[0][0]()).toEqual(
            expect.objectContaining({
                path: {
                    sample_id: 'video-1'
                }
            })
        );
        expect(get(data)).toEqual(mockVideoData);
        expect(get(error)).toBeNull();
        expect(get(isLoading)).toBe(false);
    });

    it('should cache video and only refetch when different video is requested', () => {
        const { loadById, data } = renderHook();

        mockQueryResult.data = mockVideoData;
        flushSync(() => loadById('video-1'));
        expect(createQuery).toHaveBeenCalledTimes(1);
        expect(get(data)?.sample_id).toBe('video-1');

        flushSync(() => loadById('video-1'));
        expect(createQuery).toHaveBeenCalledTimes(1);

        mockQueryResult.data = { ...mockVideoData, sample_id: 'video-2' };
        flushSync(() => loadById('video-2'));
        expect(createQuery).toHaveBeenCalledTimes(1);
        expect(get(data)?.sample_id).toBe('video-2');
    });

    it('should expose error when query fails', () => {
        const mockError = new Error('Failed to load video');
        mockQueryResult.error = mockError;

        const { data, error, isLoading, loadById } = renderHook();

        flushSync(() => loadById('video-1'));

        expect(get(data)).toBeUndefined();
        expect(get(error)).toEqual(mockError);
        expect(get(isLoading)).toBe(false);
    });

    it('should expose refetch function that invalidates queries', () => {
        mockQueryResult.data = mockVideoData;

        const { loadById, refetch } = renderHook();

        flushSync(() => loadById('video-1'));

        const refetchFn = get(refetch);
        refetchFn();

        expect(mockQueryClient.invalidateQueries).toHaveBeenCalledWith({
            queryKey: ['video', 'video-1']
        });
    });

    it('should notify subscribers when query state changes', () => {
        mockQueryResult.isLoading = true;

        const { data, error, isLoading, loadById } = renderHook();

        const dataValues: (VideoView | undefined)[] = [];
        const errorValues: (Error | null)[] = [];
        const loadingValues: boolean[] = [];

        const unsubData = data.subscribe((value) => dataValues.push(value));
        const unsubError = error.subscribe((value) => errorValues.push(value));
        const unsubLoading = isLoading.subscribe((value) => loadingValues.push(value));

        flushSync(() => loadById('video-1'));

        mockQueryResult.data = mockVideoData;
        mockQueryResult.isLoading = false;
        flushSync(() => loadById('video-2'));

        expect(dataValues[dataValues.length - 1]).toEqual(mockVideoData);
        expect(errorValues[errorValues.length - 1]).toBeNull();
        expect(loadingValues[loadingValues.length - 1]).toBe(false);

        unsubData();
        unsubError();
        unsubLoading();
    });
});
