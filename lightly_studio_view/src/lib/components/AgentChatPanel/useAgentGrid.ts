import { page } from '$app/state';
import { useQueryClient } from '@tanstack/svelte-query';
import { get } from 'svelte/store';
import type { TurnDoneEvent } from '$lib/api/lightly_studio_local';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
import { useTags } from '$lib/hooks/useTags/useTags';
import { applyUiActions } from './applyUiActions';

export function useAgentGrid(collectionId: string) {
    const queryClient = useQueryClient();
    const { getSelectedSampleIds } = useGlobalStorage();
    const { filterParams, updateSampleIds } = useImageFilters();
    const { loadTags, clearTagsSelected, setTagSelected } = useTags({
        collection_id: collectionId,
        autoLoad: false
    });
    const selectedSamples = getSelectedSampleIds(collectionId);

    function isCurrentGrid() {
        return (
            page.params.collection_id === collectionId &&
            get(filterParams).collection_id === collectionId
        );
    }

    async function onUiActions(actions: TurnDoneEvent['ui_actions']) {
        await applyUiActions(actions, {
            showTag: async (tagId) => {
                await loadTags();
                if (isCurrentGrid()) {
                    clearTagsSelected();
                    setTagSelected(tagId, true);
                    updateSampleIds([]);
                }
            },
            showSamples: (sampleIds) => {
                if (!isCurrentGrid()) return;
                clearTagsSelected();
                updateSampleIds(sampleIds);
            },
            refreshData: loadTags
        });

        if (actions.some((action) => action.type !== 'show_samples')) {
            // The filters are ready. Let active queries refetch while the user continues the chat.
            void queryClient.invalidateQueries();
        }
    }

    return { selectedSamples, onUiActions };
}
