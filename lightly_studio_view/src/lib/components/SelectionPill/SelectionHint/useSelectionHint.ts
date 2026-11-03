import { writable, type Readable, type Writable } from 'svelte/store';

export const SELECTION_HINT_STORAGE_KEY = 'lightly-studio.selection-hint-dismissed';

let dismissed: Writable<boolean> | null = null;

function loadDismissed(): boolean {
    try {
        return localStorage.getItem(SELECTION_HINT_STORAGE_KEY) === 'true';
    } catch {
        // No storage (SSR, private mode): show the hint.
        return false;
    }
}

/** Whether the "select to tag or annotate" hint was dismissed, kept in localStorage. */
export function useSelectionHint(): { dismissed: Readable<boolean>; dismiss: () => void } {
    dismissed ??= writable(loadDismissed());
    const store = dismissed;
    return {
        dismissed: store,
        dismiss: () => {
            store.set(true);
            try {
                localStorage.setItem(SELECTION_HINT_STORAGE_KEY, 'true');
            } catch {
                // The hint stays hidden for this session.
            }
        }
    };
}
