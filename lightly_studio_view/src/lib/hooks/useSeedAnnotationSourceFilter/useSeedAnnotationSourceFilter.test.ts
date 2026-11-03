import { render } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import { useAnnotationPairFilter } from '$lib/hooks/useAnnotationPairFilter/useAnnotationPairFilter';
import UseSeedAnnotationSourceFilterHarness from './UseSeedAnnotationSourceFilter.harness.svelte';

const mocks = vi.hoisted(() => ({
    collections: undefined as { collection_id: string; name: string }[] | undefined,
    seedSelectionIfNeeded: vi.fn()
}));

vi.mock('$lib/hooks/useAnnotationCollections/useAnnotationCollections', () => ({
    useAnnotationCollections: vi.fn(() => ({
        get data() {
            return mocks.collections;
        }
    }))
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

    // Review Focus 4: deleting a source with ticked pairs must not leave the grid filtering
    // on a source that no longer exists.
    it('drops the pairs of a source that left the source list', async () => {
        const gtDeer = { collection_id: 'gt', annotation_label_id: 'deer', label_name: 'deer' };
        const gtFox = { collection_id: 'gt', annotation_label_id: 'fox', label_name: 'fox' };
        const predRaccoon = {
            collection_id: 'pred',
            annotation_label_id: 'raccoon',
            label_name: 'raccoon'
        };
        const { pairs, setKnownPairs, togglePair, clear } = useAnnotationPairFilter('images-2');
        clear();
        setKnownPairs([gtDeer, gtFox, predRaccoon]);
        togglePair(gtFox);
        mocks.collections = [
            { collection_id: 'gt', name: 'Ground truth' },
            { collection_id: 'pred', name: 'Predictions' }
        ];
        const { rerender } = render(UseSeedAnnotationSourceFilterHarness, {
            collectionId: 'images-2'
        });
        expect(get(pairs)).toHaveLength(2);

        mocks.collections = [{ collection_id: 'gt', name: 'Ground truth' }];
        await rerender({ collectionId: 'images-3' });
        await rerender({ collectionId: 'images-2' });

        // The deleted source no longer appears in the ticked pairs the grid sends.
        expect(get(pairs)).toEqual([{ collection_id: 'gt', annotation_label_id: 'deer' }]);
    });
});
