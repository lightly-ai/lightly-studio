import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useSessionStorage } from './useSessionStorage';
import { get } from 'svelte/store';

describe('useSessionStorage', () => {
    // Mock sessionStorage
    const mockSessionStorage = {
        getItem: vi.fn(),
        setItem: vi.fn(),
        clear: vi.fn(),
        removeItem: vi.fn(),
        key: vi.fn(),
        length: 0
    };

    beforeEach(() => {
        // Setup the mock before each test
        vi.stubGlobal('sessionStorage', mockSessionStorage);
        // Clear all mocks
        vi.clearAllMocks();
        // Spy on console.warn
        vi.spyOn(console, 'warn').mockImplementation(() => {});
    });

    afterEach(() => {
        // Restore global mocks
        vi.unstubAllGlobals();
    });

    it('should initialize with value from sessionStorage', () => {
        const storedValue = { test: 'value' };
        mockSessionStorage.getItem.mockReturnValueOnce(JSON.stringify(storedValue));

        const store = useSessionStorage('testKey', { default: 'initial' });

        expect(mockSessionStorage.getItem).toHaveBeenCalledWith('testKey');
        expect(get(store)).toEqual(storedValue);
    });

    it('should initialize with initial value when key not in sessionStorage', () => {
        const initialValue = { default: 'initial' };
        mockSessionStorage.getItem.mockReturnValueOnce(null);

        const store = useSessionStorage('testKey', initialValue);

        expect(mockSessionStorage.getItem).toHaveBeenCalledWith('testKey');
        expect(get(store)).toEqual(initialValue);
    });

    it('should initialize with initial value when sessionStorage throws error', () => {
        const initialValue = { default: 'initial' };
        mockSessionStorage.getItem.mockImplementationOnce(() => {
            throw new Error('Storage error');
        });

        const store = useSessionStorage('testKey', initialValue);

        expect(mockSessionStorage.getItem).toHaveBeenCalledWith('testKey');
        expect(console.warn).toHaveBeenCalled();
        expect(get(store)).toEqual(initialValue);
    });

    it('should update sessionStorage when store value changes', () => {
        mockSessionStorage.getItem.mockReturnValueOnce(null);
        const store = useSessionStorage('testKey', 'initial');

        const newValue = 'updated value';
        store.set(newValue);

        expect(mockSessionStorage.setItem).toHaveBeenCalledWith(
            'testKey',
            JSON.stringify(newValue)
        );
    });

    it('should handle errors when writing to sessionStorage', () => {
        mockSessionStorage.getItem.mockReturnValueOnce(null);
        mockSessionStorage.setItem.mockImplementationOnce(() => {
            throw new Error('Storage write error');
        });

        const store = useSessionStorage('testKey', 'initial');
        store.set('new value');

        expect(console.warn).toHaveBeenCalled();
    });
});
