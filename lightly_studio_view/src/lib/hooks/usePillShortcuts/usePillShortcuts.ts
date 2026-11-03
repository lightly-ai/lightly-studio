import { derived, writable, type Readable, type Writable } from 'svelte/store';

export const PILL_SHORTCUTS_STORAGE_KEY = 'lightly-studio.pill-shortcuts';

interface PillShortcutKeys {
    tagKey: string;
    annotateKey: string;
}

const DEFAULT_KEYS: PillShortcutKeys = { tagKey: 't', annotateKey: 'l' };

let keys: Writable<PillShortcutKeys> | null = null;

function loadKeys(): PillShortcutKeys {
    try {
        const stored = JSON.parse(localStorage.getItem(PILL_SHORTCUTS_STORAGE_KEY) ?? 'null');
        return {
            tagKey: typeof stored?.tagKey === 'string' ? stored.tagKey : DEFAULT_KEYS.tagKey,
            annotateKey:
                typeof stored?.annotateKey === 'string'
                    ? stored.annotateKey
                    : DEFAULT_KEYS.annotateKey
        };
    } catch {
        // No storage (SSR, private mode) or a broken value: use the defaults.
        return DEFAULT_KEYS;
    }
}

/** The keys that open the selection pill's Tag and Annotate menus, kept in localStorage. */
export function usePillShortcuts(): {
    tagKey: Readable<string>;
    annotateKey: Readable<string>;
    setKeys: (keys: PillShortcutKeys) => void;
} {
    keys ??= writable(loadKeys());
    const store = keys;
    return {
        tagKey: derived(store, ($keys) => $keys.tagKey),
        annotateKey: derived(store, ($keys) => $keys.annotateKey),
        setKeys: (next) => {
            store.set({ ...next });
            try {
                localStorage.setItem(PILL_SHORTCUTS_STORAGE_KEY, JSON.stringify(next));
            } catch {
                // The keys still apply for this session.
            }
        }
    };
}
