import { get } from 'svelte/store';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { CUSTOM_LABEL_COLORS_STORAGE_KEY } from '$lib/constants';

// The store is a module-level singleton that loads from and subscribes to
// localStorage at import time, so each test re-imports the module after seeding
// localStorage to exercise the load/persist behavior in isolation.
const importFresh = async () => {
    vi.resetModules();
    return (await import('./useCustomLabelColors')).useCustomLabelColors;
};

beforeEach(() => {
    localStorage.clear();
});

afterEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
});

describe('useCustomLabelColors persistence', () => {
    test('loads previously persisted colors on init', async () => {
        localStorage.setItem(
            CUSTOM_LABEL_COLORS_STORAGE_KEY,
            JSON.stringify({ cat: { color: '#ff0000', alpha: 0.5 } })
        );

        const useCustomLabelColors = await importFresh();
        const { getCustomColor, hasCustomColor } = useCustomLabelColors();

        expect(hasCustomColor('cat')).toBe(true);
        expect(getCustomColor('cat')).toEqual({ color: '#ff0000', alpha: 0.5 });
    });

    test('starts empty when nothing is persisted', async () => {
        const useCustomLabelColors = await importFresh();
        const { customLabelColorsStore } = useCustomLabelColors();

        expect(get(customLabelColorsStore)).toEqual({});
    });

    test('persists colors to localStorage when set', async () => {
        const useCustomLabelColors = await importFresh();
        const { setCustomColor } = useCustomLabelColors();

        setCustomColor('dog', '#00ff00', 0.8);

        expect(JSON.parse(localStorage.getItem(CUSTOM_LABEL_COLORS_STORAGE_KEY) ?? '{}')).toEqual({
            dog: { color: '#00ff00', alpha: 0.8 }
        });
    });

    test('persisted colors survive a reload (re-import)', async () => {
        const useCustomLabelColors = await importFresh();
        useCustomLabelColors().setCustomColor('dog', '#00ff00', 0.8);

        const useCustomLabelColorsReloaded = await importFresh();
        expect(useCustomLabelColorsReloaded().getCustomColor('dog')).toEqual({
            color: '#00ff00',
            alpha: 0.8
        });
    });

    test('updates localStorage when a color is deleted', async () => {
        const useCustomLabelColors = await importFresh();
        const { setCustomColor, deleteCustomColor } = useCustomLabelColors();

        setCustomColor('dog', '#00ff00', 0.8);
        deleteCustomColor('dog');

        expect(JSON.parse(localStorage.getItem(CUSTOM_LABEL_COLORS_STORAGE_KEY) ?? '{}')).toEqual(
            {}
        );
    });

    test('clears localStorage when all colors are cleared', async () => {
        const useCustomLabelColors = await importFresh();
        const { setCustomColor, clearCustomColors } = useCustomLabelColors();

        setCustomColor('dog', '#00ff00', 0.8);
        clearCustomColors();

        expect(JSON.parse(localStorage.getItem(CUSTOM_LABEL_COLORS_STORAGE_KEY) ?? '{}')).toEqual(
            {}
        );
    });

    test('falls back to empty map when stored data is corrupt', async () => {
        localStorage.setItem(CUSTOM_LABEL_COLORS_STORAGE_KEY, 'not-json');
        const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

        const useCustomLabelColors = await importFresh();
        const { customLabelColorsStore } = useCustomLabelColors();

        expect(get(customLabelColorsStore)).toEqual({});
        expect(errorSpy).toHaveBeenCalled();
    });
});
