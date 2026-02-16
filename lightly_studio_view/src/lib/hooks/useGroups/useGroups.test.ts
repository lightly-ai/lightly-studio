import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useGroups } from './useGroups';
import type { QueryClient, CreateQueryResult } from '@tanstack/svelte-query';
import * as tanstackQuery from '@tanstack/svelte-query';

describe('useGroups Hook', () => {
    const mockInvalidateQueries = vi.fn();
    const mockQueryClient: Pick<QueryClient, 'invalidateQueries'> = {
        invalidateQueries: mockInvalidateQueries
    };

    const mockQueryResult = {
        data: {
            data: [
                {
                    sample_id: '1',
                    sample: { sample_id: '1', created_at: '2024-01-01T00:00:00Z' },
                    similarity_score: null,
                    first_sample_image: {
                        sample_id: 'img1',
                        file_name: 'image1.jpg',
                        file_path_abs: '/path/to/image1.jpg',
                        width: 1920,
                        height: 1080
                    },
                    first_sample_video: null
                },
                {
                    sample_id: '2',
                    sample: { sample_id: '2', created_at: '2024-01-02T00:00:00Z' },
                    similarity_score: null,
                    first_sample_image: null,
                    first_sample_video: {
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
            total_count: 2,
            nextCursor: null
        },
        isLoading: false,
        error: null
    };

    beforeEach(() => {
        vi.clearAllMocks();
        vi.resetAllMocks();

        vi.spyOn(tanstackQuery, 'useQueryClient').mockReturnValue(mockQueryClient as QueryClient);
        vi.spyOn(tanstackQuery, 'createQuery').mockReturnValue({
            subscribe: (fn: (value: unknown) => void) => {
                fn(mockQueryResult);
                return vi.fn();
            }
        } as CreateQueryResult<unknown, Error>);
    });

    it('should return groups and refetch function', () => {
        const { groups, refetch } = useGroups({
            path: { collection_id: '123' }
        });

        expect(groups).toBeDefined();
        expect(refetch).toBeDefined();
        expect(typeof refetch).toBe('function');
    });

    it('should call invalidateQueries when refetch is called', () => {
        const { refetch } = useGroups({
            path: { collection_id: '123' }
        });

        refetch();

        expect(mockInvalidateQueries).toHaveBeenCalledWith({
            queryKey: expect.any(Array)
        });
    });

    it('should call createQuery with correct options', () => {
        const createQuerySpy = vi.spyOn(tanstackQuery, 'createQuery');

        useGroups({
            path: { collection_id: '123' }
        });

        expect(createQuerySpy).toHaveBeenCalledWith(
            expect.objectContaining({
                queryKey: expect.any(Array)
            })
        );
    });

    it('should handle different collection_id options', () => {
        const { refetch: refetch1 } = useGroups({
            path: { collection_id: '123' }
        });

        const { refetch: refetch2 } = useGroups({
            path: { collection_id: '456' }
        });

        refetch1();
        refetch2();

        expect(mockInvalidateQueries).toHaveBeenCalledTimes(2);
    });

    it('should return groups with first_sample_image or first_sample_video', () => {
        const { groups } = useGroups({
            path: { collection_id: '123' }
        });

        let queryData: unknown;
        groups.subscribe((value) => {
            queryData = value;
        })();

        const data = (queryData as typeof mockQueryResult).data;
        expect(data).toBeDefined();
        expect(data.data).toHaveLength(2);
        expect(data.total_count).toBe(2);

        // First group has an image
        expect(data.data[0].sample_id).toBe('1');
        expect(data.data[0].first_sample_image).toBeDefined();
        expect(data.data[0].first_sample_image?.file_name).toBe('image1.jpg');
        expect(data.data[0].first_sample_video).toBeNull();

        // Second group has a video
        expect(data.data[1].sample_id).toBe('2');
        expect(data.data[1].first_sample_image).toBeNull();
        expect(data.data[1].first_sample_video).toBeDefined();
        expect(data.data[1].first_sample_video?.file_name).toBe('video1.mp4');
        expect(data.data[1].first_sample_video?.duration_s).toBe(10.5);
    });
});
