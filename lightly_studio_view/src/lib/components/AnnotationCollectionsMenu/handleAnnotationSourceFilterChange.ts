interface HandleAnnotationSourceFilterChangeParams {
    /** The new set of selected collection IDs after the user's action. */
    newIds: string[];
    /** The set of selected collection IDs before the user's action. */
    prevIds: string[];
    /** All available annotation source items with their display names. */
    items: { id: string; name: string }[];
    /** The active dataset collection ID, used as context in the analytics event. */
    collectionId: string;
    /** Updates the persisted selection of annotation source IDs. */
    setSelectedCollectionIds: (ids: string[]) => void;
    /** Fires an analytics event. */
    trackEvent: (eventName: string, properties?: Record<string, unknown>) => void;
}

export function handleAnnotationSourceFilterChange({
    newIds,
    prevIds,
    items,
    collectionId,
    setSelectedCollectionIds,
    trackEvent
}: HandleAnnotationSourceFilterChangeParams): void {
    const prevSet = new Set(prevIds);
    const nextSet = new Set(newIds);

    const addedId = newIds.find((id) => !prevSet.has(id));
    const removedId = prevIds.find((id) => !nextSet.has(id));

    const action: 'selected' | 'unselected' = addedId ? 'selected' : 'unselected';
    const changedId = addedId ?? removedId;
    const changedItem = items.find((item) => item.id === changedId);

    setSelectedCollectionIds(newIds);

    if (changedItem) {
        trackEvent('grid_filter_toggled', {
            collection_id: collectionId,
            filter_type: 'annotation_source',
            filter_value: changedItem.name,
            action,
            active_count: newIds.length
        });
    }
}
