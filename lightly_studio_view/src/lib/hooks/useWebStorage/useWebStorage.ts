import { writable, type Writable } from 'svelte/store';

export type JsonSerializable =
    | string
    | number
    | boolean
    | null
    | JsonSerializable[]
    | { [key: string]: JsonSerializable };

type StorageArea = 'localStorage' | 'sessionStorage';

/**
 * Creates a writable store that syncs with localStorage or sessionStorage
 * @param area The web storage area to use
 * @param key The storage key to use
 * @param initialValue The default value if nothing is in storage
 * @returns A writable store that automatically syncs with the storage area
 */
export function useWebStorage<T extends JsonSerializable>(
    area: StorageArea,
    key: string,
    initialValue: T
): Writable<T> {
    const getStorage = (): Storage | undefined =>
        (globalThis as unknown as Record<StorageArea, Storage | undefined>)[area];

    // Read from storage
    const initialize = (): T => {
        if (typeof getStorage() === 'undefined') {
            return initialValue;
        }
        try {
            const item = getStorage()!.getItem(key);
            if (item) {
                return JSON.parse(item);
            }
        } catch (e) {
            console.warn(`Failed to read ${key} from ${area}`, e);
        }
        return initialValue;
    };

    const store = writable<T>(initialize());

    // Keep storage in sync with store
    store.subscribe((value) => {
        const storage = getStorage();
        if (typeof storage === 'undefined') {
            return;
        }
        try {
            storage.setItem(key, JSON.stringify(value));
        } catch (e) {
            console.warn(`Failed to write ${key} to ${area}`, e);
        }
    });

    return store;
}
