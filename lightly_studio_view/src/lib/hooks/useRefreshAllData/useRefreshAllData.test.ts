import { describe, expect, it, vi } from 'vitest';
import { useQueryClient } from '@tanstack/svelte-query';
import { useTags } from '$lib/hooks/useTags/useTags';
import { useRefreshAllData } from './useRefreshAllData';

vi.mock('@tanstack/svelte-query', () => ({ useQueryClient: vi.fn() }));
vi.mock('$lib/hooks/useTags/useTags', () => ({ useTags: vi.fn() }));

describe('useRefreshAllData', () => {
    it('reloads the tags of the collection and invalidates all queries', async () => {
        const loadTags = vi.fn().mockResolvedValue(undefined);
        const invalidateQueries = vi.fn().mockResolvedValue(undefined);
        vi.mocked(useTags).mockReturnValue({ loadTags } as unknown as ReturnType<typeof useTags>);
        vi.mocked(useQueryClient).mockReturnValue({
            invalidateQueries
        } as unknown as ReturnType<typeof useQueryClient>);

        const { refreshAllData } = useRefreshAllData({ collectionId: 'col-1' });
        await refreshAllData();

        expect(useTags).toHaveBeenCalledWith({ collection_id: 'col-1' });
        expect(loadTags).toHaveBeenCalledOnce();
        expect(invalidateQueries).toHaveBeenCalledExactlyOnceWith();
    });
});
