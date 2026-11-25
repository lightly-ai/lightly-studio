import { get } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';

// The hook keeps module-level state, so each test imports a fresh module.
const importHook = async () => {
    const { useUnannotatedSamplesFilter } = await import('./useUnannotatedSamplesFilter');
    return useUnannotatedSamplesFilter();
};

describe('useUnannotatedSamplesFilter', () => {
    beforeEach(() => {
        vi.resetModules();
    });

    it('keeps the filter for the same collection', async () => {
        const { includeUnannotatedSamples, setIncludeUnannotatedSamples, scopeToCollection } =
            await importHook();

        scopeToCollection('collection-1');
        setIncludeUnannotatedSamples(true);
        scopeToCollection('collection-1');

        expect(get(includeUnannotatedSamples)).toBe(true);
    });

    it('clears the filter when the collection changes', async () => {
        const { includeUnannotatedSamples, setIncludeUnannotatedSamples, scopeToCollection } =
            await importHook();

        scopeToCollection('collection-1');
        setIncludeUnannotatedSamples(true);
        scopeToCollection('collection-2');

        expect(get(includeUnannotatedSamples)).toBe(false);
    });
});
