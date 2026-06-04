import { get } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';

// The hook keeps module-level state (the stores and the seeded-collection marker), so each
// test re-imports a fresh module to start from a clean slate.
const importHook = async () => {
    const { useAnnotationCollectionsFilter } = await import('./useAnnotationCollectionsFilter');
    return useAnnotationCollectionsFilter();
};

const sources = [
    { id: 'gt', name: 'Ground truth' },
    { id: 'pred', name: 'Predictions' }
];

describe('useAnnotationCollectionsFilter', () => {
    beforeEach(() => {
        vi.resetModules();
    });

    it('seeds every source and its name the first time a collection is shown', async () => {
        const { selectedCollectionIds, collectionIdToName, seedSelectionIfNeeded } =
            await importHook();

        seedSelectionIfNeeded('collection-1', sources);

        expect(get(selectedCollectionIds)).toEqual(['gt', 'pred']);
        expect(get(collectionIdToName)).toEqual({ gt: 'Ground truth', pred: 'Predictions' });
    });

    it('keeps an existing selection on later calls for the same collection', async () => {
        const { selectedCollectionIds, setSelectedCollectionIds, seedSelectionIfNeeded } =
            await importHook();

        seedSelectionIfNeeded('collection-1', sources);
        setSelectedCollectionIds(['gt']); // user deselects "Predictions"
        seedSelectionIfNeeded('collection-1', sources); // e.g. returning from image details

        expect(get(selectedCollectionIds)).toEqual(['gt']);
    });

    it('re-seeds all sources when the collection changes', async () => {
        const { selectedCollectionIds, setSelectedCollectionIds, seedSelectionIfNeeded } =
            await importHook();

        seedSelectionIfNeeded('collection-1', sources);
        setSelectedCollectionIds(['gt']);
        seedSelectionIfNeeded('collection-2', [
            { id: 'a', name: 'A' },
            { id: 'b', name: 'B' }
        ]);

        expect(get(selectedCollectionIds)).toEqual(['a', 'b']);
    });
});
