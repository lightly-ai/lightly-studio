import { readable, type Readable } from 'svelte/store';

export type StoreOrVal<T> = T | Readable<T>;

export function isSvelteStore<T>(val: StoreOrVal<T>): val is Readable<T> {
    return val != null && typeof val === 'object' && 'subscribe' in val;
}

export function toReadable<T>(val: StoreOrVal<T>): Readable<T> {
    return isSvelteStore(val) ? val : readable(val);
}
