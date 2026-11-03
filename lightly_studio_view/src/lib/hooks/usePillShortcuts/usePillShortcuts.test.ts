import { get } from 'svelte/store';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

describe('usePillShortcuts', () => {
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

    it('defaults to T and L', async () => {
        const { usePillShortcuts } = await import('./usePillShortcuts');
        const { tagKey, annotateKey } = usePillShortcuts();

        expect(get(tagKey)).toBe('t');
        expect(get(annotateKey)).toBe('l');
    });

    it('saves new keys and reads them back after a reload', async () => {
        const first = await import('./usePillShortcuts');
        first.usePillShortcuts().setKeys({ tagKey: 'g', annotateKey: 'k' });

        expect(get(first.usePillShortcuts().tagKey)).toBe('g');
        expect(JSON.parse(values.get(first.PILL_SHORTCUTS_STORAGE_KEY)!)).toEqual({
            tagKey: 'g',
            annotateKey: 'k'
        });

        vi.resetModules();
        const reloaded = await import('./usePillShortcuts');
        expect(get(reloaded.usePillShortcuts().annotateKey)).toBe('k');
    });

    it('falls back to the defaults on a broken stored value', async () => {
        values.set('lightly-studio.pill-shortcuts', '{not json');
        const { usePillShortcuts } = await import('./usePillShortcuts');

        expect(get(usePillShortcuts().tagKey)).toBe('t');
    });
});
