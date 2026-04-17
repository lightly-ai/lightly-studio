import { derived, get, writable, type Readable } from 'svelte/store';

const hiddenByCollection = writable<Record<string, string[]>>({});

export function useHiddenFilters(collectionId: Readable<string>) {
    const hiddenSampleIds: Readable<string[]> = derived(
        [hiddenByCollection, collectionId],
        ([$hidden, $collectionId]) => $hidden[$collectionId] ?? []
    );

    function setHidden(ids: string[]) {
        hiddenByCollection.update((current) => ({
            ...current,
            [get(collectionId)]: ids
        }));
    }

    function clearHidden() {
        setHidden([]);
    }

    return { hiddenSampleIds, setHidden, clearHidden };
}
