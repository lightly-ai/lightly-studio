import { beforeEach, describe, expect, it } from 'vitest';
import { get } from 'svelte/store';
import { useWebStorage } from './useWebStorage';

describe('useWebStorage', () => {
    beforeEach(() => {
        localStorage.clear();
        sessionStorage.clear();
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
});
