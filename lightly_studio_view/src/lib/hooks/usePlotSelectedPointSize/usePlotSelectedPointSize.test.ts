import { get } from 'svelte/store';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const STORAGE_KEY = 'lightly-studio:plot-selected-point-size';

// The store is module-level, so each test imports a fresh module after preparing storage.
async function loadHook() {
    vi.resetModules();
    const { usePlotSelectedPointSize } = await import('./usePlotSelectedPointSize');
    return usePlotSelectedPointSize();
}

describe('usePlotSelectedPointSize', () => {
    // Node 25 ships its own localStorage, which shadows jsdom's, so stub it as useOnboarding does.
    beforeEach(() => {
        const values = new Map<string, string>();
        vi.stubGlobal('localStorage', {
            getItem: (key: string) => values.get(key) ?? null,
            setItem: (key: string, value: string) => values.set(key, value)
        });
    });

    afterEach(() => vi.unstubAllGlobals());

    it('defaults to large', async () => {
        const { selectedPointSize } = await loadHook();

        expect(get(selectedPointSize)).toBe('large');
    });

    it('reads the stored size and ignores unknown values', async () => {
        localStorage.setItem(STORAGE_KEY, 'small');
        expect(get((await loadHook()).selectedPointSize)).toBe('small');

        localStorage.setItem(STORAGE_KEY, 'huge');
        expect(get((await loadHook()).selectedPointSize)).toBe('large');
    });

    it('saves a new size to localStorage', async () => {
        const { selectedPointSize } = await loadHook();

        selectedPointSize.set('extra_large');

        expect(localStorage.getItem(STORAGE_KEY)).toBe('extra_large');
    });
});
