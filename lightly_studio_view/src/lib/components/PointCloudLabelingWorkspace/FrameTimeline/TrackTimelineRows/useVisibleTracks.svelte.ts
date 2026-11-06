import type { SequenceTrackView } from '$lib/api/lightly_studio_local/types.gen';
import { getDefaultTrackKeys, getTrackKey, selectVisibleTracks } from './visibleTracks';

interface Params {
    getTracks: () => SequenceTrackView[];
    getSelectedAnnotationId: () => string | null;
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
 * Chooses which tracks the timeline lists. Until the user picks, the first tracks show.
 * Tracks that appear later (e.g. a newly created one) are added to the choice, so they never
 * vanish right after being made.
 */
export function useVisibleTracks({ getTracks, getSelectedAnnotationId, getStorageKey }: Params) {
    let storageKey: string | undefined;
    let selection = $state<string[] | null>(null);
    let knownTracks: SequenceTrackView[] | null = null;

    $effect(() => {
        const key = getStorageKey();
        const tracks = getTracks();
        if (key !== storageKey) {
            storageKey = key;
            selection = read(key);
            knownTracks = null;
        }
        if (knownTracks === null) {
            // Tracks load after the first render, so only a non-empty list is a baseline.
            if (tracks.length > 0) knownTracks = tracks;
            return;
        }
        const known = new Set(knownTracks.map(getTrackKey));
        const added = tracks.map(getTrackKey).filter((trackKey) => !known.has(trackKey));
        if (added.length > 0) {
            setSelection([...(selection ?? getDefaultTrackKeys(knownTracks)), ...added]);
        }
        knownTracks = tracks;
    });

    function setSelection(next: string[]) {
        selection = [...new Set(next)];
        write(storageKey, selection);
    }

    return {
        get visibleTracks() {
            return selectVisibleTracks(getTracks(), selection, getSelectedAnnotationId());
        },
        /** Keys of the tracks the user's choice (or the default) lists. */
        get selectedKeys() {
            return selection ?? getDefaultTrackKeys(getTracks());
        },
        setSelection
    };
}
