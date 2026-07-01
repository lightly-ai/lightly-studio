import { get } from 'svelte/store';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { CUSTOM_LABEL_COLORS_STORAGE_KEY } from '$lib/constants';
import { useLocalStorage } from '$lib/hooks/useLocalStorage/useLocalStorage';

// Persistence is owned (and tested) by useLocalStorage; here we mock it with a
// plain in-memory store and only exercise the colour-map operations and wiring.
vi.mock('$lib/hooks/useLocalStorage/useLocalStorage', async () => {
    const { writable } = await import('svelte/store');
    return {
        useLocalStorage: vi.fn((_key: string, initialValue: unknown) => writable(initialValue))
    };
});

const COLOR = { color: '#00ff00', alpha: 0.8 };

// The store is a module-level singleton, so re-import the module per test to reset it.
const load = async () => {
    vi.resetModules();
    return (await import('./useCustomLabelColors')).useCustomLabelColors();
};

beforeEach(() => vi.clearAllMocks());

afterEach(() => vi.restoreAllMocks());

describe('useCustomLabelColors', () => {
    it('starts empty', async () => {
        const { customLabelColorsStore } = await load();

        expect(get(customLabelColorsStore)).toEqual({});
    });

    it('sets and reads a custom colour', async () => {
        const { setCustomColor, getCustomColor, hasCustomColor } = await load();

        setCustomColor('dog', COLOR.color, COLOR.alpha);

        expect(hasCustomColor('dog')).toBe(true);
        expect(getCustomColor('dog')).toEqual(COLOR);
    });

    it('reports missing labels as absent', async () => {
        const { getCustomColor, hasCustomColor } = await load();

        expect(hasCustomColor('cat')).toBe(false);
        expect(getCustomColor('cat')).toBeUndefined();
    });

    it('deletes only the requested label', async () => {
        const { setCustomColor, deleteCustomColor, hasCustomColor } = await load();

        setCustomColor('dog', COLOR.color, COLOR.alpha);
        setCustomColor('cat', COLOR.color, COLOR.alpha);
        deleteCustomColor('dog');

        expect(hasCustomColor('dog')).toBe(false);
        expect(hasCustomColor('cat')).toBe(true);
    });

    it('clears all colours', async () => {
        const { setCustomColor, clearCustomColors, customLabelColorsStore } = await load();

        setCustomColor('dog', COLOR.color, COLOR.alpha);
        clearCustomColors();

        expect(get(customLabelColorsStore)).toEqual({});
    });

    it('backs the store with the custom-label-colours storage key', async () => {
        await load();

        expect(useLocalStorage).toHaveBeenCalledWith(
            CUSTOM_LABEL_COLORS_STORAGE_KEY,
            {},
            expect.any(Function)
        );
    });

    it('validates payloads through a parser that drops malformed entries', async () => {
        await load();
        const parse = vi.mocked(useLocalStorage).mock.calls.at(-1)?.[2];

        expect(parse?.({ cat: COLOR, bad: 123, arr: [1] })).toEqual({ cat: COLOR });
        expect(parse?.('not an object')).toEqual({});
        expect(parse?.([COLOR])).toEqual({});
    });
});
