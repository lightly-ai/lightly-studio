import { derived, get, writable, type Readable } from 'svelte/store';

const selectedCollectionIds = writable<string[]>([]);
const collectionIdToName = writable<Record<string, string>>({});

// The sources the filter knows about, which are the annotation sources of the collection the
// user is looking at. Follows the source list rather than the selection, so a source created
// while the collection is open can still be hidden.
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

// True while the filter knows about sources and the user has unchecked all of them. Nothing is
// drawn in that state, so nothing counted per source should survive either.
const allSourcesHidden: Readable<boolean> = derived(
    [selectedCollectionIds, knownSourceIds],
    ([$ids, $known]) => $known.size > 0 && $ids.length === 0
);

// Annotations are colored per source instead of per class while more than one source is
// visible. Pass this to resolveEffectiveColorBySource rather than reading the selection length.
const multipleSourcesVisible: Readable<boolean> = derived(
    selectedCollectionIds,
    ($ids) => $ids.length > 1
);

// Remembers which annotation collection the grid filter was last seeded for.
// Module-level so it survives component remounts (e.g. grid <-> image details), which lets
// the user's source selection persist within a collection. Each collection keeps its own
// selection, see selectionByCollection.
// useSeedAnnotationSourceFilter calls the seeder for every collection the user opens, so the
// selection always describes the collection on screen and never leaks across tabs.
let seededCollectionId: string | undefined;
// Source selections of the collections the user left, so each tab gets its own back for the
// session.
const selectionByCollection = new Map<
    string,
    { selectedIds: string[]; idToName: Record<string, string> }
>();

export const useAnnotationCollectionsFilter = () => {
    return {
        selectedCollectionIds,
        setSelectedCollectionIds: (ids: string[]) => selectedCollectionIds.set(ids),
        isSourceVisible,
        allSourcesHidden,
        multipleSourcesVisible,
        collectionIdToName,
        setCollectionIdToName: (map: Record<string, string>) => collectionIdToName.set(map),
        /**
         * Points the filter at a collection's annotation sources.
         *
         * The first call for a collection selects every source. Later calls for the same
         * collection keep the user's selection and fold in sources that appeared since, because
         * an annotation can be written to a brand-new source and the filter can only hide what
         * it knows about. Switching to a collection selects everything the first time and gives
         * back the selection the user left there afterwards, so a selection never leaks across
         * collections.
         */
        seedSelectionIfNeeded: (
            collectionId: string,
            collections: { id: string; name: string }[]
        ) => {
            const nextIdToName = Object.fromEntries(collections.map((c) => [c.id, c.name]));

            if (seededCollectionId !== collectionId) {
                if (seededCollectionId) {
                    selectionByCollection.set(seededCollectionId, {
                        selectedIds: get(selectedCollectionIds),
                        idToName: get(collectionIdToName)
                    });
                }
                seededCollectionId = collectionId;
                const saved = selectionByCollection.get(collectionId);
                collectionIdToName.set(nextIdToName);
                selectedCollectionIds.set(
                    collections
                        .map((c) => c.id)
                        .filter(
                            (id) =>
                                !saved || saved.selectedIds.includes(id) || !(id in saved.idToName)
                        )
                );
                return;
            }

            // Same collection, but the source list can still grow: an annotation may be written
            // to a brand-new source, and the filter can only hide sources it knows about.
            const previousIdToName = get(collectionIdToName);
            const unchanged =
                Object.keys(previousIdToName).length === collections.length &&
                collections.every((c) => previousIdToName[c.id] === c.name);
            if (unchanged) return;

            const addedIds = collections.map((c) => c.id).filter((id) => !(id in previousIdToName));

            collectionIdToName.set(nextIdToName);
            // A new source starts checked, so an annotation just drawn into one stays on screen.
            selectedCollectionIds.update(($ids) => [
                ...$ids.filter((id) => id in nextIdToName),
                ...addedIds
            ]);
        }
    };
};
