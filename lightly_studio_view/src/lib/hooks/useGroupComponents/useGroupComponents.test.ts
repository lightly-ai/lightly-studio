import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useGroupComponents } from './useGroupComponents';
import type { QueryClient, CreateQueryResult } from '@tanstack/svelte-query';
import * as tanstackQuery from '@tanstack/svelte-query';
import { get } from 'svelte/store';

describe('useGroupComponents Hook', () => {
    const mockInvalidateQueries = vi.fn();
    const mockQueryClient: Pick<QueryClient, 'invalidateQueries'> = {
        invalidateQueries: mockInvalidateQueries
    };

    const mockGroupComponents = [
        {
            collection: {
                collection_id: 'col1',
                group_component_name: 'front'
            },
            details: {
                sample_id: 'img1',
                file_name: 'front_0.jpg',
                file_path_abs: '/path/to/front_0.jpg',
                width: 1920,
                height: 1080,
                type: 'image'
            }
        },
        {
            collection: {
                collection_id: 'col2',
                group_component_name: 'back'
            },
            details: {
                sample_id: 'img2',
                file_name: 'back_0.jpg',
                file_path_abs: '/path/to/back_0.jpg',
                width: 1920,
                height: 1080,
                type: 'image'
            }
        }
    ];

    const mockQueryResult = {
        data: mockGroupComponents,
        isSuccess: true,
        isLoading: false,
        error: null
    };

    beforeEach(() => {
        vi.resetAllMocks();

        vi.spyOn(tanstackQuery, 'useQueryClient').mockReturnValue(mockQueryClient as QueryClient);
        vi.spyOn(tanstackQuery, 'createQuery').mockReturnValue({
            subscribe: (fn: (value: unknown) => void) => {
                fn(mockQueryResult);
                return vi.fn();
            }
        } as CreateQueryResult<unknown, Error>);
    });

    it('should return groupComponents and refetch', () => {
        const result = useGroupComponents({ groupId: 'group123' });

        expect(result.groupComponents).toBeDefined();
        expect(result.refetch).toBeDefined();
        expect(typeof result.refetch).toBe('function');
    });

    it('should call invalidateQueries when refetch is called', () => {
        const { refetch } = useGroupComponents({ groupId: 'group123' });

        refetch();

        expect(mockInvalidateQueries).toHaveBeenCalledWith({
            queryKey: expect.any(Array)
        });
    });

    it('should call createQuery with correct options', () => {
        const createQuerySpy = vi.spyOn(tanstackQuery, 'createQuery');

        useGroupComponents({ groupId: 'group123' });

        expect(createQuerySpy).toHaveBeenCalledWith(
            expect.objectContaining({
                queryKey: expect.any(Array)
            })
        );
    });

    it('should return group components data', () => {
        const { groupComponents } = useGroupComponents({ groupId: 'group123' });

        const data = get(groupComponents).data;
        expect(data).toHaveLength(2);
        expect(data?.[0].collection.group_component_name).toBe('front');
        expect(data?.[1].collection.group_component_name).toBe('back');
    });

    it('should handle different group IDs', () => {
        const { refetch: refetch1 } = useGroupComponents({ groupId: 'group1' });
        const { refetch: refetch2 } = useGroupComponents({ groupId: 'group2' });

        refetch1();
        refetch2();

        expect(mockInvalidateQueries).toHaveBeenCalledTimes(2);
    });
});
