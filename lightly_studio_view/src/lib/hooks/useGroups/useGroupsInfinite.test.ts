import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useGroupsInfinite } from './useGroupsInfinite';
import type { QueryClient, CreateInfiniteQueryResult } from '@tanstack/svelte-query';
import * as tanstackQuery from '@tanstack/svelte-query';
import { get } from 'svelte/store';

describe('useGroupsInfinite Hook', () => {
    const mockInvalidateQueries = vi.fn();
    const mockQueryClient: Pick<QueryClient, 'invalidateQueries'> = {
        invalidateQueries: mockInvalidateQueries
    };

    const mockPage1 = {
        data: [
            {
                sample_id: '1',
                sample: { sample_id: '1', created_at: '2024-01-01T00:00:00Z' },
                similarity_score: null,
                group_snapshot: {
                    sample_id: 'img1',
                    file_name: 'image1.jpg',
                    file_path_abs: '/path/to/image1.jpg',
                    width: 1920,
                    height: 1080
                }
            },
            {
                sample_id: '2',
                sample: { sample_id: '2', created_at: '2024-01-02T00:00:00Z' },
                similarity_score: null,
                group_snapshot: {
                    sample_id: 'vid1',
                    file_name: 'video1.mp4',
                    file_path_abs: '/path/to/video1.mp4',
                    width: 1920,
                    height: 1080,
                    duration_s: 10.5,
                    fps: 30
                }
            }
        ],
        total_count: 3,
        nextCursor: 'cursor-page-2'
    };

    const mockPage2 = {
        data: [
            {
                sample_id: '3',
                sample: { sample_id: '3', created_at: '2024-01-03T00:00:00Z' },
                similarity_score: null,
                group_snapshot: {
                    sample_id: 'img3',
                    file_name: 'image3.jpg',
                    file_path_abs: '/path/to/image3.jpg',
                    width: 1920,
                    height: 1080
                }
            }
        ],
        total_count: 3,
        nextCursor: null
    };

    const mockQueryResult = {
        data: {
            pages: [mockPage1],
            pageParams: [undefined]
        },
        isSuccess: true,
        isLoading: false,
        hasNextPage: true,
        isFetchingNextPage: false,
        fetchNextPage: vi.fn(),
        error: null
    };

    beforeEach(() => {
        vi.clearAllMocks();
        vi.resetAllMocks();

        vi.spyOn(tanstackQuery, 'useQueryClient').mockReturnValue(mockQueryClient as QueryClient);
        vi.spyOn(tanstackQuery, 'createInfiniteQuery').mockReturnValue({
            subscribe: (fn: (value: unknown) => void) => {
                fn(mockQueryResult);
                return vi.fn();
            }
        } as CreateInfiniteQueryResult<unknown, Error>);
    });

    it('should return data, loadMore, query, refresh, and totalCount', () => {
        const result = useGroupsInfinite('123');

        expect(result.data).toBeDefined();
        expect(result.loadMore).toBeDefined();
        expect(result.query).toBeDefined();
        expect(result.refresh).toBeDefined();
        expect(result.totalCount).toBeDefined();
        expect(typeof result.loadMore).toBe('function');
        expect(typeof result.refresh).toBe('function');
    });

    it('should call invalidateQueries when refresh is called', () => {
        const { refresh } = useGroupsInfinite('123');

        refresh();

        expect(mockInvalidateQueries).toHaveBeenCalledWith({
            queryKey: expect.any(Array)
        });
    });

    it('should call createInfiniteQuery with correct options', () => {
        const createInfiniteQuerySpy = vi.spyOn(tanstackQuery, 'createInfiniteQuery');

        useGroupsInfinite('123');

        expect(createInfiniteQuerySpy).toHaveBeenCalledWith(
            expect.objectContaining({
                queryKey: expect.any(Array),
                getNextPageParam: expect.any(Function)
            })
        );
    });

    it('should flatten pages into data store', () => {
        const { data } = useGroupsInfinite('123');

        const groups = get(data);
        expect(groups).toHaveLength(2);
        expect(groups[0].sample_id).toBe('1');
        expect(groups[1].sample_id).toBe('2');
    });

    it('should set totalCount from first page', () => {
        const { totalCount } = useGroupsInfinite('123');

        expect(get(totalCount)).toBe(3);
    });

    it('should handle groups with group_snapshot', () => {
        const { data } = useGroupsInfinite('123');

        const groups = get(data);

        // First group has a snapshot (image)
        expect(groups[0].group_snapshot).toBeDefined();
        expect(groups[0].group_snapshot?.file_name).toBe('image1.jpg');

        // Second group has a snapshot (video)
        expect(groups[1].group_snapshot).toBeDefined();
        expect(groups[1].group_snapshot?.file_name).toBe('video1.mp4');
        expect(groups[1].group_snapshot?.duration_s).toBe(10.5);
    });

    it('should call fetchNextPage when loadMore is called and hasNextPage is true', () => {
        const mockFetchNextPage = vi.fn();
        const mockQueryWithNext = {
            ...mockQueryResult,
            hasNextPage: true,
            isFetchingNextPage: false,
            fetchNextPage: mockFetchNextPage
        };

        vi.spyOn(tanstackQuery, 'createInfiniteQuery').mockReturnValue({
            subscribe: (fn: (value: unknown) => void) => {
                fn(mockQueryWithNext);
                return vi.fn();
            }
        } as CreateInfiniteQueryResult<unknown, Error>);

        const { loadMore, query } = useGroupsInfinite('123');

        // Mock the get(query) to return our mock
        vi.spyOn(query, 'subscribe').mockImplementation((fn: (value: unknown) => void) => {
            fn(mockQueryWithNext);
            return vi.fn();
        });

        loadMore();

        expect(mockFetchNextPage).toHaveBeenCalled();
    });

    it('should not call fetchNextPage when isFetchingNextPage is true', () => {
        const mockFetchNextPage = vi.fn();
        const mockQueryFetching = {
            ...mockQueryResult,
            hasNextPage: true,
            isFetchingNextPage: true,
            fetchNextPage: mockFetchNextPage
        };

        vi.spyOn(tanstackQuery, 'createInfiniteQuery').mockReturnValue({
            subscribe: (fn: (value: unknown) => void) => {
                fn(mockQueryFetching);
                return vi.fn();
            }
        } as CreateInfiniteQueryResult<unknown, Error>);

        const { loadMore, query } = useGroupsInfinite('123');

        // Mock the get(query) to return our mock
        vi.spyOn(query, 'subscribe').mockImplementation((fn: (value: unknown) => void) => {
            fn(mockQueryFetching);
            return vi.fn();
        });

        loadMore();

        expect(mockFetchNextPage).not.toHaveBeenCalled();
    });

    it('should not call fetchNextPage when hasNextPage is false', () => {
        const mockFetchNextPage = vi.fn();
        const mockQueryNoNext = {
            ...mockQueryResult,
            hasNextPage: false,
            isFetchingNextPage: false,
            fetchNextPage: mockFetchNextPage
        };

        vi.spyOn(tanstackQuery, 'createInfiniteQuery').mockReturnValue({
            subscribe: (fn: (value: unknown) => void) => {
                fn(mockQueryNoNext);
                return vi.fn();
            }
        } as CreateInfiniteQueryResult<unknown, Error>);

        const { loadMore, query } = useGroupsInfinite('123');

        // Mock the get(query) to return our mock
        vi.spyOn(query, 'subscribe').mockImplementation((fn: (value: unknown) => void) => {
            fn(mockQueryNoNext);
            return vi.fn();
        });

        loadMore();

        expect(mockFetchNextPage).not.toHaveBeenCalled();
    });

    it('should handle multiple pages of data', () => {
        const mockQueryMultiPage = {
            ...mockQueryResult,
            data: {
                pages: [mockPage1, mockPage2],
                pageParams: [undefined, 'cursor-page-2']
            }
        };

        vi.spyOn(tanstackQuery, 'createInfiniteQuery').mockReturnValue({
            subscribe: (fn: (value: unknown) => void) => {
                fn(mockQueryMultiPage);
                return vi.fn();
            }
        } as CreateInfiniteQueryResult<unknown, Error>);

        const { data, totalCount } = useGroupsInfinite('123');

        const groups = get(data);
        expect(groups).toHaveLength(3);
        expect(groups[0].sample_id).toBe('1');
        expect(groups[1].sample_id).toBe('2');
        expect(groups[2].sample_id).toBe('3');
        expect(get(totalCount)).toBe(3);
    });

    it('should handle different collection_id', () => {
        const { refresh: refresh1 } = useGroupsInfinite('123');
        const { refresh: refresh2 } = useGroupsInfinite('456');

        refresh1();
        refresh2();

        expect(mockInvalidateQueries).toHaveBeenCalledTimes(2);
    });
});
