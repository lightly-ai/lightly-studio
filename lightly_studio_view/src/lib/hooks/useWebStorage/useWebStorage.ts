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
 * Creates a writable store that syncs with localStorage or sessionStorage. A localStorage store
 * also follows writes from other tabs, so two tabs do not overwrite each other's values.
 * @param area The web storage area to use
 * @param key The storage key to use
 * @param initialValue The default value if nothing usable is in storage
 * @returns A writable store that automatically syncs with the storage area
 */
export function useWebStorage<T extends JsonSerializable>(
    area: StorageArea,
    key: string,
    initialValue: T
): Writable<T> {
    const getStorage = (): Storage | undefined =>
        (globalThis as unknown as Record<StorageArea, Storage | undefined>)[area];

    const parse = (readItem: () => string | null | undefined): T => {
        try {
            const item = readItem();
            return item ? withShapeOf(initialValue, JSON.parse(item)) : initialValue;
        } catch (e) {
            console.warn(`Failed to read ${key} from ${area}`, e);
            return initialValue;
        }
    };

    const store = writable<T>(parse(() => getStorage()?.getItem(key)));

    // The JSON in storage as this store last saw it. A value that came from another tab is not
    // written back, so the tabs do not echo each other.
    let storedJson: string | null = null;

    store.subscribe((value) => {
        const storage = getStorage();
        if (typeof storage === 'undefined') {
            return;
        }
        try {
            const json = JSON.stringify(value);
            if (json === storedJson) return;
            storedJson = json;
            storage.setItem(key, json);
        } catch (e) {
            console.warn(`Failed to write ${key} to ${area}`, e);
        }
    });

    // Only localStorage is shared between tabs.
    if (area === 'localStorage' && typeof window !== 'undefined') {
        window.addEventListener('storage', (event) => {
            if (event.key !== key || event.storageArea !== getStorage()) return;
            storedJson = event.newValue;
            store.set(parse(() => event.newValue));
        });
    }

    return store;
}

/** Returns `value`, or `initialValue` when the two differ in shape: object, array or primitive. */
const withShapeOf = <T extends JsonSerializable>(initialValue: T, value: JsonSerializable): T => {
    if (initialValue === null) return value as T;
    return shapeOf(value) === shapeOf(initialValue) ? (value as T) : initialValue;
};

const shapeOf = (value: JsonSerializable): string => {
    if (value === null) return 'null';
    if (Array.isArray(value)) return 'array';
    return typeof value;
};
