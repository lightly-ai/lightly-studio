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

    it('learns a source that appears after the first seed', async () => {
        const { isSourceVisible, setSelectedCollectionIds, seedSelectionIfNeeded } =
            await importHook();

        seedSelectionIfNeeded('collection-1', sources);
        // an annotation was written to a brand-new source, so the list refetches longer
        seedSelectionIfNeeded('collection-1', [...sources, { id: 'new', name: 'Manual' }]);
        setSelectedCollectionIds(['gt', 'pred']);

        expect(get(isSourceVisible)('new')).toBe(false);
    });

    it('keeps the selection and checks the source that appeared', async () => {
        const { selectedCollectionIds, setSelectedCollectionIds, seedSelectionIfNeeded } =
            await importHook();

        seedSelectionIfNeeded('collection-1', sources);
        setSelectedCollectionIds(['gt']);
        seedSelectionIfNeeded('collection-1', [...sources, { id: 'new', name: 'Manual' }]);

        expect(get(selectedCollectionIds)).toEqual(['gt', 'new']);
    });

    it('drops a source that is gone from the list', async () => {
        const { selectedCollectionIds, collectionIdToName, seedSelectionIfNeeded } =
            await importHook();

        seedSelectionIfNeeded('collection-1', sources);
        seedSelectionIfNeeded('collection-1', [{ id: 'gt', name: 'Ground truth' }]);

        expect(get(selectedCollectionIds)).toEqual(['gt']);
        expect(get(collectionIdToName)).toEqual({ gt: 'Ground truth' });
    });

    it('does not notify subscribers when the source list is unchanged', async () => {
        const { isSourceVisible, seedSelectionIfNeeded } = await importHook();

        seedSelectionIfNeeded('collection-1', sources);

        let emissions = 0;
        const unsubscribe = isSourceVisible.subscribe(() => {
            emissions += 1;
        });
        seedSelectionIfNeeded('collection-1', sources); // e.g. a window-focus refetch
        unsubscribe();

        expect(emissions).toBe(1); // the subscribe call itself
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

    describe('isSourceVisible', () => {
        it('shows only the selected sources', async () => {
            const { isSourceVisible, setSelectedCollectionIds, seedSelectionIfNeeded } =
                await importHook();

            seedSelectionIfNeeded('collection-1', sources);
            setSelectedCollectionIds(['gt']);

            expect(get(isSourceVisible)('gt')).toBe(true);
            expect(get(isSourceVisible)('pred')).toBe(false);
        });

        it('hides every source once the user unchecks them all', async () => {
            const { isSourceVisible, setSelectedCollectionIds, seedSelectionIfNeeded } =
                await importHook();

            seedSelectionIfNeeded('collection-1', sources);
            setSelectedCollectionIds([]);

            expect(get(isSourceVisible)('gt')).toBe(false);
            expect(get(isSourceVisible)('pred')).toBe(false);
        });

        // The videos grid draws frame annotations whose sources hang off the frames
        // collection, so they are absent from the videos collection's own source list.
        // The filter has no say over them and must not hide them.
        it('shows a source it does not know about', async () => {
            const { isSourceVisible, setSelectedCollectionIds, seedSelectionIfNeeded } =
                await importHook();

            seedSelectionIfNeeded('collection-1', sources);
            setSelectedCollectionIds([]);

            expect(get(isSourceVisible)('source-from-the-frames-collection')).toBe(true);
        });

        it('shows everything before any collection has been seeded', async () => {
            const { isSourceVisible } = await importHook();

            expect(get(isSourceVisible)('gt')).toBe(true);
        });
    });

    describe('allSourcesHidden', () => {
        it('is false before any collection has been seeded', async () => {
            const { allSourcesHidden } = await importHook();

            expect(get(allSourcesHidden)).toBe(false);
        });

        it('is false while a source is still selected', async () => {
            const { allSourcesHidden, setSelectedCollectionIds, seedSelectionIfNeeded } =
                await importHook();

            seedSelectionIfNeeded('collection-1', sources);
            setSelectedCollectionIds(['gt']);

            expect(get(allSourcesHidden)).toBe(false);
        });

        it('is true once the user unchecks every source', async () => {
            const { allSourcesHidden, setSelectedCollectionIds, seedSelectionIfNeeded } =
                await importHook();

            seedSelectionIfNeeded('collection-1', sources);
            setSelectedCollectionIds([]);

            expect(get(allSourcesHidden)).toBe(true);
        });

        // A collection without annotation sources has an empty selection too, but the user
        // never hid anything, so the counts must stay as they are.
        it('is false for a collection that has no sources', async () => {
            const { allSourcesHidden, seedSelectionIfNeeded } = await importHook();

            seedSelectionIfNeeded('collection-1', []);

            expect(get(allSourcesHidden)).toBe(false);
        });
    });

    describe('multipleSourcesVisible', () => {
        it('is true only while more than one source is selected', async () => {
            const { multipleSourcesVisible, setSelectedCollectionIds, seedSelectionIfNeeded } =
                await importHook();

            expect(get(multipleSourcesVisible)).toBe(false);

            seedSelectionIfNeeded('collection-1', sources);
            expect(get(multipleSourcesVisible)).toBe(true);

            setSelectedCollectionIds(['gt']);
            expect(get(multipleSourcesVisible)).toBe(false);
        });
    });
});
