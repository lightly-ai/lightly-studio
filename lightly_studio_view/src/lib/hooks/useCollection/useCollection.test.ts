import { describe, expect, it, vi } from 'vitest';
import { useQueryClient } from '@tanstack/svelte-query';
import { useInvalidateCollectionHierarchyQueries } from './useCollection';

vi.mock('@tanstack/svelte-query', async (importOriginal) => {
    const actual = await importOriginal<typeof import('@tanstack/svelte-query')>();
    return { ...actual, useQueryClient: vi.fn() };
});

describe('useInvalidateCollectionHierarchyQueries', () => {
    it('invalidates the collection hierarchy of every dataset', () => {
        const invalidateQueries = vi.fn();
        vi.mocked(useQueryClient).mockReturnValue({ invalidateQueries } as unknown as ReturnType<
            typeof useQueryClient
        >);

        useInvalidateCollectionHierarchyQueries()();

        expect(invalidateQueries).toHaveBeenCalledWith({
            queryKey: [{ _id: 'readCollectionHierarchy' }]
        });
    });
});
