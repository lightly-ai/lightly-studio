import { writable, type Writable } from 'svelte/store';

type JsonSerializable =
    | string
    | number
    | boolean
    | null
    | JsonSerializable[]
    | { [key: string]: JsonSerializable };

/**
 * Creates a writable store that syncs with localStorage, so the value survives a reload and a new
 * tab. Two open tabs do not see each other's writes: the last write wins.
 * @param key The localStorage key to use
 * @param initialValue The default value if nothing is in storage
 * @returns A writable store that automatically syncs with localStorage
 */
export function useLocalStorage<T extends JsonSerializable>(
    key: string,
    initialValue: T
): Writable<T> {
    const initialize = (): T => {
        try {
            const item = localStorage.getItem(key);
            if (item) return JSON.parse(item);
        } catch (e) {
            console.warn(`Failed to read ${key} from localStorage`, e);
        }
        return initialValue;
    };

    const store = writable<T>(typeof localStorage === 'undefined' ? initialValue : initialize());

    store.subscribe((value) => {
        if (typeof localStorage === 'undefined') return;
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (e) {
            console.warn(`Failed to write ${key} to localStorage`, e);
        }
    });

    return store;
}
