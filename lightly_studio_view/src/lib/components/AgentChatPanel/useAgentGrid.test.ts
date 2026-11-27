import { writable } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';
import { useAgentGrid } from './useAgentGrid';

const mocks = vi.hoisted(() => ({
    invalidateQueries: vi.fn(),
    loadTags: vi.fn(),
    setTagSelected: vi.fn(),
    updateSampleIds: vi.fn()
}));

vi.mock('$app/state', () => ({ page: { params: { collection_id: 'collection' } } }));
vi.mock('@tanstack/svelte-query', () => ({
    useQueryClient: () => ({ invalidateQueries: mocks.invalidateQueries })
}));
vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({ getSelectedSampleIds: () => writable(new Set<string>()) })
}));
vi.mock('$lib/hooks/useImageFilters/useImageFilters', () => ({
    useImageFilters: () => ({
        filterParams: writable({ collection_id: 'collection' }),
        updateSampleIds: mocks.updateSampleIds
    })
}));
vi.mock('$lib/hooks/useTags/useTags', () => ({
    useTags: () => ({
        loadTags: mocks.loadTags,
        clearTagsSelected: vi.fn(),
        setTagSelected: mocks.setTagSelected
    })
}));

describe('useAgentGrid', () => {
    it('finishes applying the tag while active queries are still refetching', async () => {
        const refetch = Promise.withResolvers<void>();
        mocks.invalidateQueries.mockReturnValue(refetch.promise);
        const { onUiActions } = useAgentGrid('collection');

        await onUiActions([{ type: 'select_tag', tag_id: 'tag', tag_name: 'Picked' }]);

        expect(mocks.loadTags).toHaveBeenCalledOnce();
        expect(mocks.setTagSelected).toHaveBeenCalledWith('tag', true);
        expect(mocks.updateSampleIds).toHaveBeenCalledWith([]);
        expect(mocks.invalidateQueries).toHaveBeenCalledOnce();
        refetch.resolve();
    });
});
