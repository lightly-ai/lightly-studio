import { derived, get, writable, type Readable } from 'svelte/store';
import type { SourceLabelPair } from '$lib/api/lightly_studio_local';

type SourceState = 'checked' | 'partial' | 'unchecked';

// Ticked (annotation source, annotation class) pairs per collection. Each grid tab is its own
// collection, so every tab keeps its own pairs for the session.
const pairsByCollection = writable<Record<string, SourceLabelPair[]>>({});

const isSamePair = (pair: SourceLabelPair, sourceId: string, labelId: string) =>
    pair.collection_id === sourceId && pair.annotation_label_id === labelId;

/** Whether all, some or none of a source's classes are ticked. */
export const getSourceState = (
    pairs: SourceLabelPair[],
    sourceId: string,
    labelIds: string[]
): SourceState => {
    const ticked = labelIds.filter((labelId) =>
        pairs.some((pair) => isSamePair(pair, sourceId, labelId))
    ).length;
    if (ticked === 0) return 'unchecked';
    return ticked === labelIds.length ? 'checked' : 'partial';
};

/**
 * The annotation filter of the images and annotations grids, as exact (annotation source,
 * annotation class) pairs. A tick on "deer" under ground_truth matches only deer in
 * ground_truth. No pair means no annotation filter.
 */
export function useAnnotationPairFilter(collectionId: string) {
    const pairs: Readable<SourceLabelPair[]> = derived(
        pairsByCollection,
        ($byCollection) => $byCollection[collectionId] ?? []
    );

    const update = (fn: (current: SourceLabelPair[]) => SourceLabelPair[]) =>
        pairsByCollection.update(($byCollection) => ({
            ...$byCollection,
            [collectionId]: fn($byCollection[collectionId] ?? [])
        }));

    const togglePair = (sourceId: string, labelId: string) =>
        update((current) =>
            current.some((pair) => isSamePair(pair, sourceId, labelId))
                ? current.filter((pair) => !isSamePair(pair, sourceId, labelId))
                : [...current, { collection_id: sourceId, annotation_label_id: labelId }]
        );

    const setSource = (sourceId: string, labelIds: string[], checked: boolean) =>
        update((current) => {
            const others = current.filter(
                (pair) =>
                    pair.collection_id !== sourceId || !labelIds.includes(pair.annotation_label_id)
            );
            if (!checked) return others;
            return [
                ...others,
                ...labelIds.map((labelId) => ({
                    collection_id: sourceId,
                    annotation_label_id: labelId
                }))
            ];
        });

    const sourceState = (sourceId: string, labelIds: string[]) =>
        getSourceState(get(pairs), sourceId, labelIds);

    const dropSource = (sourceId: string) =>
        update((current) => current.filter((pair) => pair.collection_id !== sourceId));

    const clear = () => update(() => []);

    return { pairs, togglePair, setSource, sourceState, dropSource, clear };
}
