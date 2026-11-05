import { writable, type Writable } from 'svelte/store';

/**
 * Creates a writable store that syncs with sessionStorage
 * @param key The sessionStorage key to use
 * @param initialValue The default value if nothing is in storage
 * @returns A writable store that automatically syncs with sessionStorage
 */
type JsonSerializable =
    | string
    | number
    | boolean
    | null
    | JsonSerializable[]
    | { [key: string]: JsonSerializable };
export function useSessionStorage<T extends JsonSerializable>(
    key: string,
    initialValue: T
): Writable<T> {
    // Read from sessionStorage
    const initialize = (): T => {
        if (typeof sessionStorage === 'undefined') {
            return initialValue;
        }
        try {
            const item = sessionStorage.getItem(key);
            if (item) {
                return JSON.parse(item);
            }
        } catch (e) {
            console.warn(`Failed to read ${key} from sessionStorage`, e);
        }
        return initialValue;
    };

    const store = writable<T>(initialize());

    // Keep sessionStorage in sync with store
    store.subscribe((value) => {
        if (typeof sessionStorage === 'undefined') {
            return;
        }
        try {
            sessionStorage.setItem(key, JSON.stringify(value));
        } catch (e) {
            console.warn(`Failed to write ${key} to sessionStorage`, e);
        }
    });

    return store;
}
