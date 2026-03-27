import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useVideo } from './useVideo';
import { writable, get } from 'svelte/store';
import type { VideoView } from '$lib/api/lightly_studio_local/types.gen';
import { createQuery, useQueryClient } from '@tanstack/svelte-query';

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

    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(useQueryClient).mockReturnValue(
            mockQueryClient as ReturnType<typeof useQueryClient>
        );
    });

    it('should initialize with undefined data, null error, and false isLoading', () => {
        const { data, error, isLoading } = useVideo();

        expect(get(data)).toBeUndefined();
        expect(get(error)).toBeNull();
        expect(get(isLoading)).toBe(false);
    });

    it('should load video data by sample_id', () => {
        const mockQueryStore = writable({
            data: mockVideoData,
            error: null,
            isLoading: false
        });
        vi.mocked(createQuery).mockReturnValue(mockQueryStore as ReturnType<typeof createQuery>);

        const { data, error, isLoading, loadById } = useVideo();

        loadById('video-1');

        expect(createQuery).toHaveBeenCalledWith(
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
        const mockQueryStore1 = writable({
            data: mockVideoData,
            error: null,
            isLoading: false
        });
        const mockQueryStore2 = writable({
            data: { ...mockVideoData, sample_id: 'video-2' },
            error: null,
            isLoading: false
        });

        vi.mocked(createQuery)
            .mockReturnValueOnce(mockQueryStore1 as ReturnType<typeof createQuery>)
            .mockReturnValueOnce(mockQueryStore2 as ReturnType<typeof createQuery>);

        const { loadById, data } = useVideo();

        // First load
        loadById('video-1');
        expect(createQuery).toHaveBeenCalledTimes(1);
        expect(get(data)?.sample_id).toBe('video-1');

        // Try loading same video again - should not refetch
        loadById('video-1');
        expect(createQuery).toHaveBeenCalledTimes(1);

        // Load different video - should refetch
        loadById('video-2');
        expect(createQuery).toHaveBeenCalledTimes(2);
        expect(get(data)?.sample_id).toBe('video-2');
    });

    it('should expose error when query fails', () => {
        const mockError = new Error('Failed to load video');
        const mockQueryStore = writable({
            data: undefined,
            error: mockError,
            isLoading: false
        });
        vi.mocked(createQuery).mockReturnValue(mockQueryStore as ReturnType<typeof createQuery>);

        const { data, error, isLoading, loadById } = useVideo();

        loadById('video-1');

        expect(get(data)).toBeUndefined();
        expect(get(error)).toEqual(mockError);
        expect(get(isLoading)).toBe(false);
    });

    it('should expose refetch function that invalidates queries', () => {
        const mockQueryStore = writable({
            data: mockVideoData,
            error: null,
            isLoading: false
        });
        vi.mocked(createQuery).mockReturnValue(mockQueryStore as ReturnType<typeof createQuery>);

        const { loadById, refetch } = useVideo();

        loadById('video-1');

        const refetchFn = get(refetch);
        refetchFn();

        expect(mockQueryClient.invalidateQueries).toHaveBeenCalledWith({
            queryKey: ['video', 'video-1']
        });
    });

    it('should notify subscribers when query state changes', () => {
        const mockQueryStore = writable({
            data: undefined,
            error: null,
            isLoading: true
        });
        vi.mocked(createQuery).mockReturnValue(mockQueryStore as ReturnType<typeof createQuery>);

        const { data, error, isLoading, loadById } = useVideo();

        const dataValues: (VideoView | undefined)[] = [];
        const errorValues: (Error | null)[] = [];
        const loadingValues: boolean[] = [];

        const unsubData = data.subscribe((value) => dataValues.push(value));
        const unsubError = error.subscribe((value) => errorValues.push(value));
        const unsubLoading = isLoading.subscribe((value) => loadingValues.push(value));

        loadById('video-1');

        // Simulate query completion
        mockQueryStore.set({
            data: mockVideoData,
            error: null,
            isLoading: false
        });

        expect(dataValues[dataValues.length - 1]).toEqual(mockVideoData);
        expect(errorValues[errorValues.length - 1]).toBeNull();
        expect(loadingValues[loadingValues.length - 1]).toBe(false);

        unsubData();
        unsubError();
        unsubLoading();
    });
});
