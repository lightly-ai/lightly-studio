import type { TagView as Tag } from '$lib/services/types';

interface ToggleTagSelectionParams {
    /** The ID of the tag to toggle. */
    tagId: string;
    /** The active dataset collection ID, used as context in the analytics event. */
    collectionId: string;
    /** The current set of selected tag IDs for this collection. */
    currentSelected: Set<string>;
    /** All available tags for this collection, used to resolve the tag's display name. */
    allTags: Tag[];
    /** Updates the persisted selection for the collection after the toggle. */
    updateSelected: (collectionId: string, newSelected: Set<string>) => void;
    /** Fires an analytics event. */
    trackEvent: (eventName: string, properties?: Record<string, unknown>) => void;
}

export function toggleTagSelection({
    tagId,
    collectionId,
    currentSelected,
    allTags,
    updateSelected,
    trackEvent
}: ToggleTagSelectionParams): void {
    const action: 'selected' | 'unselected' = currentSelected.has(tagId)
        ? 'unselected'
        : 'selected';

    const newSelected = new Set(currentSelected);
    if (action === 'unselected') {
        newSelected.delete(tagId);
    } else {
        newSelected.add(tagId);
    }

    updateSelected(collectionId, newSelected);

    const tag = allTags.find((t) => t.tag_id === tagId);
    const filter_value = tag?.name ?? tagId;

    trackEvent('grid_filter_toggled', {
        collection_id: collectionId,
        filter_type: 'tag',
        filter_value,
        action,
        active_count: newSelected.size
    });
}
