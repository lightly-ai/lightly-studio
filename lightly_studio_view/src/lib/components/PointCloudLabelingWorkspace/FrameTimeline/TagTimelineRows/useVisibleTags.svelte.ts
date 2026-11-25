import type { TickTagView } from '$lib/api/lightly_studio_local/types.gen';
import { getDefaultTagIds, selectVisibleTags } from './visibleTags';

interface Params {
    getTags: () => TickTagView[];
    /** Identifies the sequence the choice belongs to; undefined keeps it in memory only. */
    getStorageKey: () => string | undefined;
}

const read = (key: string | undefined): string[] | null => {
    if (!key) return null;
    try {
        const value = JSON.parse(localStorage.getItem(key) ?? 'null');
        return Array.isArray(value) && value.every((item) => typeof item === 'string')
            ? value
            : null;
    } catch {
        return null;
    }
};

const write = (key: string | undefined, value: string[]) => {
    if (!key) return;
    try {
        localStorage.setItem(key, JSON.stringify(value));
    } catch {
        // Storage can be unavailable; the choice then lasts until the page reloads.
    }
};

/**
 * Chooses which frame tags the timeline lists. Until the user picks, the first tags show.
 * Tags that appear later (e.g. a newly created one) are added to the user's choice, so they
 * never vanish right after being made. The default stays the first tags.
 */
export function useVisibleTags({ getTags, getStorageKey }: Params) {
    let storageKey: string | undefined;
    let selection = $state<string[] | null>(null);
    let knownTags: TickTagView[] | null = null;

    $effect(() => {
        const key = getStorageKey();
        const tags = getTags();
        if (key !== storageKey) {
            storageKey = key;
            selection = read(key);
            knownTags = null;
        }
        if (tags.length === 0) return;
        if (knownTags === null) {
            knownTags = tags;
            return;
        }
        const known = new Set(knownTags.map((tag) => tag.tag_id));
        const added = tags.map((tag) => tag.tag_id).filter((tagId) => !known.has(tagId));
        if (selection !== null && added.length > 0) {
            setSelection([...selection, ...added]);
        }
        knownTags = tags;
    });

    function setSelection(next: string[]) {
        selection = [...new Set(next)];
        write(storageKey, selection);
    }

    return {
        get visibleTags() {
            return selectVisibleTags(getTags(), selection);
        },
        /** Ids of the tags the user's choice (or the default) lists. */
        get selectedIds() {
            return selection ?? getDefaultTagIds(getTags());
        },
        setSelection
    };
}
