import type { Writable } from 'svelte/store';
import { useWebStorage, type JsonSerializable } from '../useWebStorage/useWebStorage';

/**
 * Creates a writable store that syncs with sessionStorage
 * @param key The sessionStorage key to use
 * @param initialValue The default value if nothing is in storage
 * @returns A writable store that automatically syncs with sessionStorage
 */
export function useSessionStorage<T extends JsonSerializable>(
    key: string,
    initialValue: T
): Writable<T> {
    return useWebStorage('sessionStorage', key, initialValue);
}
