import { beforeEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import { useLocalStorage } from './useLocalStorage';

describe('useLocalStorage', () => {
    beforeEach(() => {
        localStorage.clear();
        vi.restoreAllMocks();
        vi.spyOn(console, 'warn').mockImplementation(() => {});
    });

    it('starts with the stored value', () => {
        localStorage.setItem('k', '{"a":1}');

        expect(get(useLocalStorage('k', {}))).toEqual({ a: 1 });
    });

    it('starts with the initial value when nothing usable is stored', () => {
        expect(get(useLocalStorage('k', { a: 0 }))).toEqual({ a: 0 });

        localStorage.setItem('k', 'not json');
        expect(get(useLocalStorage('k', { a: 0 }))).toEqual({ a: 0 });
    });

    it('writes every change to localStorage', () => {
        const store = useLocalStorage<Record<string, number>>('k', {});

        store.set({ a: 2 });

        expect(localStorage.getItem('k')).toBe('{"a":2}');
    });

    it('stores a string with quotes and reads it back', () => {
        useLocalStorage<string>('k', 'initial').set('ground truth');

        expect(localStorage.getItem('k')).toBe('"ground truth"');
        expect(get(useLocalStorage<string>('k', 'initial'))).toBe('ground truth');
    });

    it('keeps working when a write fails', () => {
        const store = useLocalStorage<string>('k', 'initial');
        vi.spyOn(Storage.prototype, 'setItem').mockImplementationOnce(() => {
            throw new Error('QuotaExceededError');
        });

        store.set('next');

        expect(get(store)).toBe('next');
        expect(console.warn).toHaveBeenCalled();
    });
});
