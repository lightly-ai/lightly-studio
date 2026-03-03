import type { Readable } from 'svelte/store';

export const isReadableStore = <T>(value: unknown): value is Readable<T> => {
    return (
        value != null &&
        typeof value === 'object' &&
        typeof (value as { subscribe?: unknown }).subscribe === 'function'
    );
};
