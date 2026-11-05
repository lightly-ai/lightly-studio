import { beforeEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import { useWebStorage } from './useWebStorage';

const writeFromOtherTab = (key: string | null, newValue: string | null) => {
    window.dispatchEvent(new StorageEvent('storage', { key, newValue, storageArea: localStorage }));
};

describe('useWebStorage', () => {
    beforeEach(() => {
        localStorage.clear();
        sessionStorage.clear();
        vi.restoreAllMocks();
    });

    it('writes the store value to localStorage', () => {
        const store = useWebStorage<Record<string, number>>('localStorage', 'k', {});

        store.set({ a: 1 });

        expect(localStorage.getItem('k')).toBe('{"a":1}');
        expect(sessionStorage.getItem('k')).toBeNull();
    });

    it('starts from the value a previous store wrote', () => {
        useWebStorage<Record<string, number>>('localStorage', 'k', {}).set({ a: 1 });

        const second = useWebStorage<Record<string, number>>('localStorage', 'k', {});

        expect(get(second)).toEqual({ a: 1 });
    });

    it.each([
        ['null', 'null'],
        ['an array', '[1,2]'],
        ['a number', '3'],
        ['invalid JSON', '{oops']
    ])('starts from the initial value when storage holds %s', (_, stored) => {
        vi.spyOn(console, 'warn').mockImplementation(() => {});
        localStorage.setItem('k', stored);

        const store = useWebStorage<Record<string, number>>('localStorage', 'k', {});

        expect(get(store)).toEqual({});
    });

    it('takes the value another tab writes', () => {
        const store = useWebStorage<Record<string, number>>('localStorage', 'k', {});
        store.set({ a: 1 });

        localStorage.setItem('k', '{"a":1,"b":2}');
        writeFromOtherTab('k', '{"a":1,"b":2}');

        expect(get(store)).toEqual({ a: 1, b: 2 });
        store.update((value) => ({ ...value, c: 3 }));
        expect(JSON.parse(localStorage.getItem('k')!)).toEqual({ a: 1, b: 2, c: 3 });
    });

    it('does not write a value from another tab back to storage', () => {
        const store = useWebStorage<Record<string, number>>('localStorage', 'k', {});
        const setItem = vi.spyOn(Storage.prototype, 'setItem');

        writeFromOtherTab('k', '{"a":1}');

        expect(get(store)).toEqual({ a: 1 });
        expect(setItem).not.toHaveBeenCalled();
    });

    it('ignores other keys and resets when another tab removes the key', () => {
        const store = useWebStorage<Record<string, number>>('localStorage', 'k', {});
        store.set({ a: 1 });

        writeFromOtherTab('other', '{"b":2}');
        expect(get(store)).toEqual({ a: 1 });

        writeFromOtherTab('k', null);
        expect(get(store)).toEqual({});
    });

    it('resets without writing back when another tab clears the storage', () => {
        const store = useWebStorage<Record<string, number>>('localStorage', 'k', {});
        store.set({ a: 1 });
        const setItem = vi.spyOn(Storage.prototype, 'setItem');

        writeFromOtherTab(null, null);

        expect(get(store)).toEqual({});
        expect(setItem).not.toHaveBeenCalled();
    });
});
