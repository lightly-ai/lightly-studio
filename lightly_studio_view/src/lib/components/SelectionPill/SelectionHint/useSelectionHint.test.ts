import { get } from 'svelte/store';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

describe('useSelectionHint', () => {
    let values: Map<string, string>;

    beforeEach(() => {
        values = new Map<string, string>();
        vi.stubGlobal('localStorage', {
            getItem: (key: string) => values.get(key) ?? null,
            setItem: (key: string, value: string) => values.set(key, value)
        });
        vi.resetModules();
    });

    afterEach(() => vi.unstubAllGlobals());

    it('shows the hint until it is dismissed, also after a reload', async () => {
        const first = await import('./useSelectionHint');
        expect(get(first.useSelectionHint().dismissed)).toBe(false);

        first.useSelectionHint().dismiss();
        vi.resetModules();
        const reloaded = await import('./useSelectionHint');

        expect(get(reloaded.useSelectionHint().dismissed)).toBe(true);
    });
});
