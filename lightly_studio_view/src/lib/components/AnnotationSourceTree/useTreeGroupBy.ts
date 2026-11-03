import { derived, writable } from 'svelte/store';
import type { GroupBy } from './groupPairRows';

// The grouping per collection, so each grid tab keeps its own for the session.
const groupByCollection = writable<Record<string, GroupBy>>({});

/** Whether the annotation filter tree of a tab groups by source or by class. */
export function useTreeGroupBy(collectionId: string) {
    return {
        groupBy: derived(
            groupByCollection,
            ($byCollection) => $byCollection[collectionId] ?? 'source'
        ),
        setGroupBy: (groupBy: GroupBy) =>
            groupByCollection.update(($byCollection) => ({
                ...$byCollection,
                [collectionId]: groupBy
            }))
    };
}
