import { derived, get, writable } from 'svelte/store';

const exclusions = writable<Record<string, Set<string>>>({});

export function useTagExclusions(collectionId: string) {
    const excludedTagIds = derived(exclusions, (all) => all[collectionId] ?? new Set<string>());
    function setExcluded(tagId: string, excluded: boolean) {
        const ids = new Set(get(excludedTagIds));
        if (excluded) ids.add(tagId);
        else ids.delete(tagId);
        exclusions.update((all) => ({ ...all, [collectionId]: ids }));
    }
    function clearExclusions() {
        exclusions.update((all) => ({ ...all, [collectionId]: new Set<string>() }));
    }
    return { excludedTagIds, setExcluded, clearExclusions };
}
