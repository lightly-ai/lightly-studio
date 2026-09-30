import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useQueryClient } from '@tanstack/svelte-query';
import { toast } from 'svelte-sonner';
import { loadCollectionTags } from '$lib/hooks';
import { useRefreshAllData } from './useRefreshAllData';

vi.mock('@tanstack/svelte-query', () => ({ useQueryClient: vi.fn() }));
vi.mock('$lib/hooks', () => ({ loadCollectionTags: vi.fn() }));
vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn() } }));

describe('useRefreshAllData', () => {
    const invalidateQueries = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(loadCollectionTags).mockResolvedValue(undefined);
        invalidateQueries.mockResolvedValue(undefined);
        vi.mocked(useQueryClient).mockReturnValue({
            invalidateQueries
        } as unknown as ReturnType<typeof useQueryClient>);
    });

    it('reloads the tags of the given collection and invalidates all queries', async () => {
        const { refreshAllData } = useRefreshAllData();
        expect(loadCollectionTags).not.toHaveBeenCalled();

        await refreshAllData('col-1');

        expect(loadCollectionTags).toHaveBeenCalledExactlyOnceWith('col-1');
        expect(invalidateQueries).toHaveBeenCalledExactlyOnceWith();
    });

    it('shows an error toast instead of rejecting when the tags fail to load', async () => {
        vi.mocked(loadCollectionTags).mockRejectedValueOnce(new Error('network'));

        await expect(useRefreshAllData().refreshAllData('col-1')).resolves.toBeUndefined();

        expect(toast.error).toHaveBeenCalledExactlyOnceWith('Failed to refresh tags.');
        expect(invalidateQueries).toHaveBeenCalledOnce();
    });
});
