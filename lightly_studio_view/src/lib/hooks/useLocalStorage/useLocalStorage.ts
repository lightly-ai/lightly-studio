import { writable, type Writable } from 'svelte/store';

type JsonSerializable =
    | string
    | number
    | boolean
    | null
    | JsonSerializable[]
    | { [key: string]: JsonSerializable };

/**
 * Creates a writable store that syncs with localStorage.
 * @param key The localStorage key to use
 * @param initialValue The default value when nothing is stored (or on the server)
 * @param parse Optional validator/normalizer applied to the parsed JSON before it
 *   is used, so corrupt or unexpected payloads can be rejected. Defaults to identity.
 * @returns A writable store that automatically syncs with localStorage
 */
export function useLocalStorage<T extends JsonSerializable>(
    key: string,
    initialValue: T,
    parse: (value: unknown) => T = (value) => value as T
): Writable<T> {
    const initialize = (): T => {
        if (typeof localStorage === 'undefined') {
            return initialValue;
        }
        try {
            const item = localStorage.getItem(key);
            return item ? parse(JSON.parse(item)) : initialValue;
        } catch (error) {
            console.warn(`Failed to read ${key} from localStorage`, error);
            return initialValue;
        }
    };

    const store = writable<T>(initialize());

    store.subscribe((value) => {
        if (typeof localStorage === 'undefined') {
            return;
        }
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (error) {
            console.warn(`Failed to write ${key} to localStorage`, error);
        }
    });

    return store;
}
