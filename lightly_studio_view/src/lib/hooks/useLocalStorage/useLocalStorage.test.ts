import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useLocalStorage } from './useLocalStorage';
import { get } from 'svelte/store';

describe('useLocalStorage', () => {
    const mockLocalStorage = {
        getItem: vi.fn(),
        setItem: vi.fn(),
        clear: vi.fn(),
        removeItem: vi.fn(),
        key: vi.fn(),
        length: 0
    };

    beforeEach(() => {
        vi.stubGlobal('localStorage', mockLocalStorage);
        vi.clearAllMocks();
        vi.spyOn(console, 'warn').mockImplementation(() => {});
    });

    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it('should initialize with value from localStorage', () => {
        const storedValue = { test: 'value' };
        mockLocalStorage.getItem.mockReturnValueOnce(JSON.stringify(storedValue));

        const store = useLocalStorage('testKey', { default: 'initial' });

        expect(mockLocalStorage.getItem).toHaveBeenCalledWith('testKey');
        expect(get(store)).toEqual(storedValue);
    });

    it('should initialize with initial value when key not in localStorage', () => {
        const initialValue = { default: 'initial' };
        mockLocalStorage.getItem.mockReturnValueOnce(null);

        const store = useLocalStorage('testKey', initialValue);

        expect(get(store)).toEqual(initialValue);
    });

    it('should initialize with initial value when localStorage throws error', () => {
        const initialValue = { default: 'initial' };
        mockLocalStorage.getItem.mockImplementationOnce(() => {
            throw new Error('Storage error');
        });

        const store = useLocalStorage('testKey', initialValue);

        expect(console.warn).toHaveBeenCalled();
        expect(get(store)).toEqual(initialValue);
    });

    it('should run the parse transform over the stored value', () => {
        mockLocalStorage.getItem.mockReturnValueOnce(JSON.stringify({ keep: 1, drop: 2 }));

        const store = useLocalStorage<Record<string, number>>('testKey', {}, (value) =>
            Object.fromEntries(Object.entries(value as object).filter(([k]) => k === 'keep'))
        );

        expect(get(store)).toEqual({ keep: 1 });
    });

    it('should fall back to the initial value when the stored value is corrupt', () => {
        mockLocalStorage.getItem.mockReturnValueOnce('not-json');

        const store = useLocalStorage('testKey', { fallback: true });

        expect(console.warn).toHaveBeenCalled();
        expect(get(store)).toEqual({ fallback: true });
    });

    it('should update localStorage when the store value changes', () => {
        mockLocalStorage.getItem.mockReturnValueOnce(null);
        const store = useLocalStorage<string>('testKey', 'initial');

        store.set('updated value');

        expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
            'testKey',
            JSON.stringify('updated value')
        );
    });

    it('should handle errors when writing to localStorage', () => {
        mockLocalStorage.getItem.mockReturnValueOnce(null);

        const store = useLocalStorage<string>('testKey', 'initial');

        // Construction subscribes synchronously and writes the initial value, so
        // reset here to isolate the .set() write path from that first write.
        vi.mocked(console.warn).mockClear();
        mockLocalStorage.setItem.mockImplementationOnce(() => {
            throw new Error('Storage write error');
        });

        store.set('new value');

        expect(console.warn).toHaveBeenCalled();
    });
});
