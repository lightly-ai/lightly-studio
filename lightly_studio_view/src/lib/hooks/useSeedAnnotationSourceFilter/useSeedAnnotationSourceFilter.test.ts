import { render } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import UseSeedAnnotationSourceFilterHarness from './UseSeedAnnotationSourceFilter.harness.svelte';

const mocks = vi.hoisted(() => ({
    collections: undefined as { collection_id: string; name: string }[] | undefined,
    seedSelectionIfNeeded: vi.fn()
}));

vi.mock('$lib/hooks/useAnnotationCollections/useAnnotationCollections', () => ({
    useAnnotationCollections: vi.fn(() => ({ data: mocks.collections }))
}));

vi.mock('$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter', () => ({
    useAnnotationCollectionsFilter: vi.fn(() => ({
        seedSelectionIfNeeded: mocks.seedSelectionIfNeeded
    }))
}));

describe('useSeedAnnotationSourceFilter', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mocks.collections = undefined;
    });

    it('waits for the sources query before seeding', () => {
        render(UseSeedAnnotationSourceFilterHarness, { collectionId: 'images-1' });

        expect(mocks.seedSelectionIfNeeded).not.toHaveBeenCalled();
    });

    it('seeds with every source of the collection on screen', () => {
        mocks.collections = [
            { collection_id: 'gt', name: 'Ground truth' },
            { collection_id: 'pred', name: 'Predictions' }
        ];

        render(UseSeedAnnotationSourceFilterHarness, { collectionId: 'images-1' });

        expect(mocks.seedSelectionIfNeeded).toHaveBeenCalledWith('images-1', [
            { id: 'gt', name: 'Ground truth' },
            { id: 'pred', name: 'Predictions' }
        ]);
    });

    // The Annotation Sources menu hides itself for a single source. Seeding still has to run,
    // otherwise the selection stays unloaded and no boxes are drawn.
    it('seeds a collection that has a single source', () => {
        mocks.collections = [{ collection_id: 'gt', name: 'Ground truth' }];

        render(UseSeedAnnotationSourceFilterHarness, { collectionId: 'images-1' });

        expect(mocks.seedSelectionIfNeeded).toHaveBeenCalledWith('images-1', [
            { id: 'gt', name: 'Ground truth' }
        ]);
    });

    // Every grid draws boxes against one shared selection, so a tab without the menu still
    // has to replace it. seedSelectionIfNeeded keys on the collection id and does the swap.
    it('seeds a collection that has no sources at all', () => {
        mocks.collections = [];

        render(UseSeedAnnotationSourceFilterHarness, { collectionId: 'videos-1' });

        expect(mocks.seedSelectionIfNeeded).toHaveBeenCalledWith('videos-1', []);
    });
});
