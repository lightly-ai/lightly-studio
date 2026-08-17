import { derived, writable, type Readable } from 'svelte/store';

const selectedCollectionIds = writable<string[]>([]);
const collectionIdToName = writable<Record<string, string>>({});

// Whether annotations from a given source should be drawn. An empty selection means the filter
// has not been seeded for this collection yet, so nothing is filtered out.
const isSourceVisible: Readable<(sourceId: string) => boolean> = derived(
    selectedCollectionIds,
    ($ids) => (sourceId: string) => $ids.length === 0 || $ids.includes(sourceId)
);

// Annotations are colored per source instead of per class while more than one source is
// visible. Pass this to resolveEffectiveColorBySource rather than reading the selection length.
const multipleSourcesVisible: Readable<boolean> = derived(
    selectedCollectionIds,
    ($ids) => $ids.length > 1
);

// Remembers which annotation collection the grid filter was last seeded for.
// Module-level so it survives component remounts (e.g. grid <-> image details), which lets
// the user's source selection persist within a dataset while still resetting to
// "all selected" when switching to a different collection/dataset.
let seededCollectionId: string | undefined;

export const useAnnotationCollectionsFilter = () => {
    return {
        selectedCollectionIds,
        setSelectedCollectionIds: (ids: string[]) => selectedCollectionIds.set(ids),
        isSourceVisible,
        multipleSourcesVisible,
        collectionIdToName,
        setCollectionIdToName: (map: Record<string, string>) => collectionIdToName.set(map),
        /**
         * Seeds the filter with every source selected the first time a collection is shown.
         * No-op on later calls for the same collection, so a user's manual selection is
         * preserved across navigation; re-seeds when the collection changes so a stale
         * selection never leaks across datasets.
         */
        seedSelectionIfNeeded: (
            collectionId: string,
            collections: { id: string; name: string }[]
        ) => {
            if (seededCollectionId === collectionId) return;
            seededCollectionId = collectionId;
            selectedCollectionIds.set(collections.map((c) => c.id));
            collectionIdToName.set(Object.fromEntries(collections.map((c) => [c.id, c.name])));
        }
    };
};
