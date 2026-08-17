import { derived, writable, type Readable } from 'svelte/store';

const selectedCollectionIds = writable<string[]>([]);
const collectionIdToName = writable<Record<string, string>>({});

// The sources the filter knows about, which are the annotation sources of the collection the
// user is looking at. Seeded together with the selection, so its keys are always in step.
const knownSourceIds: Readable<Set<string>> = derived(
    collectionIdToName,
    ($idToName) => new Set(Object.keys($idToName))
);

// Whether annotations from a given source should be drawn.
//
// An unknown source is drawn. Not every collection owns the sources of the annotations shown
// on it: video frame annotations hang off the frames collection while the user is on the
// videos tab, so this filter has nothing to say about them. Only sources it knows about, and
// which the user has therefore had a chance to uncheck, can be hidden. That is what makes
// unchecking the last source hide the last source rather than switching the filter off.
const isSourceVisible: Readable<(sourceId: string) => boolean> = derived(
    [selectedCollectionIds, knownSourceIds],
    ([$ids, $known]) =>
        (sourceId: string) =>
            !$known.has(sourceId) || $ids.includes(sourceId)
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
// useSeedAnnotationSourceFilter calls the seeder for every collection the user opens, so the
// selection always describes the collection on screen and never leaks across tabs.
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
