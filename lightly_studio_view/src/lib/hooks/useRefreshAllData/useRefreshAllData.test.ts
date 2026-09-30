import { describe, expect, it, vi } from 'vitest';
import { useQueryClient } from '@tanstack/svelte-query';
import { loadCollectionTags } from '$lib/hooks';
import { useRefreshAllData } from './useRefreshAllData';

vi.mock('@tanstack/svelte-query', () => ({ useQueryClient: vi.fn() }));
vi.mock('$lib/hooks', () => ({ loadCollectionTags: vi.fn() }));

describe('useRefreshAllData', () => {
    it('reloads the tags of the given collection and invalidates all queries', async () => {
        const invalidateQueries = vi.fn().mockResolvedValue(undefined);
        vi.mocked(useQueryClient).mockReturnValue({
            invalidateQueries
        } as unknown as ReturnType<typeof useQueryClient>);

        const { refreshAllData } = useRefreshAllData();
        expect(loadCollectionTags).not.toHaveBeenCalled();

        await refreshAllData('col-1');

        expect(loadCollectionTags).toHaveBeenCalledExactlyOnceWith('col-1');
        expect(invalidateQueries).toHaveBeenCalledExactlyOnceWith();
    });
});
