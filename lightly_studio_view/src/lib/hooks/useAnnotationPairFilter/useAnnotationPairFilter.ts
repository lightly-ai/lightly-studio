import { derived, get, writable, type Readable } from 'svelte/store';
import {
    DEFAULT_PAIR_FILTER_STATE,
    isFilterActive,
    isSamePair,
    isSamePairList,
    toPairRequest,
    type NamedPair,
    type PairFilterState
} from './pairFilter.helpers';

// The annotation filter per collection. Each grid tab is its own collection, so every tab keeps
// its own ticks for the session.
const stateByCollection = writable<Record<string, PairFilterState>>({});
// The collection on screen. Its ticks decide which annotations the overlays draw.
const activeCollectionId = writable('');

/**
 * The annotation filter of the images and annotations grids, as (annotation source, annotation
 * class) pairs. Everything starts ticked. A tick both filters the grid and draws the annotations
 * of that pair on tiles and in the sample details view.
 *
 * Only the unticked pairs are stored, so sources and classes that appear later start ticked.
 */
export function useAnnotationPairFilter(collectionId: string) {
    const state: Readable<PairFilterState> = derived(
        stateByCollection,
        ($byCollection) => $byCollection[collectionId] ?? DEFAULT_PAIR_FILTER_STATE
    );
    const request = derived(state, toPairRequest);

    const update = (fn: (current: PairFilterState) => Partial<PairFilterState>) =>
        stateByCollection.update(($byCollection) => {
            const current = $byCollection[collectionId] ?? DEFAULT_PAIR_FILTER_STATE;
            return { ...$byCollection, [collectionId]: { ...current, ...fn(current) } };
        });

    return {
        unticked: derived(state, ($state) => $state.unticked),
        unannotatedTicked: derived(state, ($state) => $state.unannotatedTicked),
        /** The pairs to send. Empty while everything is ticked. */
        pairs: derived(request, ($request) => $request.pairs),
        /** Whether to also send the images without annotations. */
        includeUnannotated: derived(request, ($request) => $request.includeUnannotated),
        isActive: derived(state, isFilterActive),
        setKnownPairs: (known: NamedPair[]) => {
            if (!isSamePairList(get(state).known, known)) update(() => ({ known }));
        },
        setUnticked: (unticked: NamedPair[]) => update(() => ({ unticked })),
        setUnannotatedTicked: (unannotatedTicked: boolean) => update(() => ({ unannotatedTicked })),
        togglePair: (pair: NamedPair) =>
            update(({ unticked }) => ({
                unticked: unticked.some((item) => isSamePair(item, pair))
                    ? unticked.filter((item) => !isSamePair(item, pair))
                    : [...unticked, pair]
            })),
        dropSource: (sourceId: string) =>
            update(({ unticked, known }) => ({
                unticked: unticked.filter((pair) => pair.collection_id !== sourceId),
                known: known.filter((pair) => pair.collection_id !== sourceId)
            })),
        /** Ticks everything again. */
        clear: () => update(() => ({ unticked: [], unannotatedTicked: true }))
    };
}

/** Marks the collection on screen, whose ticks the overlays follow. */
export const setActivePairFilterCollection = (collectionId: string) =>
    activeCollectionId.set(collectionId);

/**
 * Whether an annotation of this source and class is drawn: its pair is ticked in the filter of
 * the collection on screen.
 */
export const isAnnotationShown: Readable<(sourceId: string, className: string) => boolean> =
    derived([stateByCollection, activeCollectionId], ([$byCollection, $activeId]) => {
        const unticked = $byCollection[$activeId]?.unticked ?? [];
        return (sourceId: string, className: string) =>
            !unticked.some(
                (pair) => pair.collection_id === sourceId && pair.label_name === className
            );
    });
