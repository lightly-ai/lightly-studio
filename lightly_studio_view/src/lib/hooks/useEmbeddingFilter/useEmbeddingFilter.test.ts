import { describe, it, expect, beforeEach, vi } from 'vitest';
import { get, writable } from 'svelte/store';
import { useHiddenFilters } from './useHiddenFilters';
import { useEmbeddingFilterForImages } from './useEmbeddingFilterForImages';
import { useEmbeddingFilterForVideos } from './useEmbeddingFilterForVideos';
import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';

vi.mock('$lib/hooks/useMetadataFilters/useMetadataFilters', () => ({
    createMetadataFilters: vi.fn(() => [])
}));

describe('useHiddenFilters', () => {
    const collectionId = writable('coll-1');

    beforeEach(() => {
        const { clearHidden } = useHiddenFilters(collectionId);
        clearHidden();
    });

    it('returns empty array initially', () => {
        const { hiddenSampleIds } = useHiddenFilters(collectionId);
        expect(get(hiddenSampleIds)).toEqual([]);
    });

    it('stores hidden IDs for the collection', () => {
        const { hiddenSampleIds, setHidden } = useHiddenFilters(collectionId);
        setHidden(['id-1', 'id-2']);
        expect(get(hiddenSampleIds)).toEqual(['id-1', 'id-2']);
    });

    it('clears hidden IDs', () => {
        const { hiddenSampleIds, setHidden, clearHidden } = useHiddenFilters(collectionId);
        setHidden(['id-1']);
        clearHidden();
        expect(get(hiddenSampleIds)).toEqual([]);
    });

    it('does not affect other collections', () => {
        const otherCollectionId = writable('coll-other');
        const { clearHidden: clearOther } = useHiddenFilters(otherCollectionId);
        clearOther();

        const { hiddenSampleIds: hidden1, setHidden } = useHiddenFilters(collectionId);
        const { hiddenSampleIds: hidden2 } = useHiddenFilters(otherCollectionId);

        setHidden(['id-1']);

        expect(get(hidden1)).toEqual(['id-1']);
        expect(get(hidden2)).toEqual([]);
    });

    it('reflects the active collection when collectionId store changes', () => {
        const dynamicId = writable('coll-a');
        const { clearHidden: clearA } = useHiddenFilters(dynamicId);
        clearA();

        const collBId = writable('coll-b');
        const { clearHidden: clearB } = useHiddenFilters(collBId);
        clearB();

        const { hiddenSampleIds, setHidden } = useHiddenFilters(dynamicId);

        dynamicId.set('coll-a');
        setHidden(['a-id']);
        dynamicId.set('coll-b');
        setHidden(['b-id']);

        dynamicId.set('coll-a');
        expect(get(hiddenSampleIds)).toEqual(['a-id']);

        dynamicId.set('coll-b');
        expect(get(hiddenSampleIds)).toEqual(['b-id']);
    });
});

describe('useEmbeddingFilterForImages', () => {
    const collectionId = writable('coll-1');
    const setRangeSelection = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        const { updateFilterParams } = useImageFilters();
        updateFilterParams({ collection_id: 'coll-1', mode: 'normal' });
        const { clearHidden } = useHiddenFilters(collectionId);
        clearHidden();
    });

    it('isVisible is false when collection_id does not match', () => {
        const { updateFilterParams } = useImageFilters();
        updateFilterParams({
            collection_id: 'other-coll',
            mode: 'normal',
            filters: { sample_ids: ['id-1'] }
        });

        const { isVisible } = useEmbeddingFilterForImages(collectionId, setRangeSelection);
        expect(get(isVisible)).toBe(false);
    });

    it('isVisible is false when mode is not normal', () => {
        const { updateFilterParams } = useImageFilters();
        updateFilterParams({
            collection_id: 'coll-1',
            mode: 'classifier'
        });

        const { isVisible } = useEmbeddingFilterForImages(collectionId, setRangeSelection);
        expect(get(isVisible)).toBe(false);
    });

    it('isVisible is true when collection matches and sample_ids are set', () => {
        const { updateFilterParams } = useImageFilters();
        updateFilterParams({
            collection_id: 'coll-1',
            mode: 'normal',
            filters: { sample_ids: ['id-1', 'id-2'] }
        });

        const { isVisible, effectiveCount } = useEmbeddingFilterForImages(
            collectionId,
            setRangeSelection
        );
        expect(get(isVisible)).toBe(true);
        expect(get(effectiveCount)).toBe(2);
    });

    it('setVisibility(false) moves active IDs to hidden and clears the filter', () => {
        const { updateFilterParams } = useImageFilters();
        updateFilterParams({
            collection_id: 'coll-1',
            mode: 'normal',
            filters: { sample_ids: ['id-1', 'id-2'] }
        });

        const { isVisible, effectiveCount, setVisibility } = useEmbeddingFilterForImages(
            collectionId,
            setRangeSelection
        );
        setVisibility(false);

        expect(get(isVisible)).toBe(false);
        expect(get(effectiveCount)).toBe(2);
    });

    it('setVisibility(true) restores previously hidden IDs', () => {
        const { updateFilterParams } = useImageFilters();
        updateFilterParams({
            collection_id: 'coll-1',
            mode: 'normal',
            filters: { sample_ids: ['id-1', 'id-2'] }
        });

        const { isVisible, effectiveCount, setVisibility } = useEmbeddingFilterForImages(
            collectionId,
            setRangeSelection
        );
        setVisibility(false);
        setVisibility(true);

        expect(get(isVisible)).toBe(true);
        expect(get(effectiveCount)).toBe(2);
    });

    it('setVisibility(true) keeps hidden IDs when restore cannot be applied', () => {
        const { updateFilterParams } = useImageFilters();
        updateFilterParams({
            collection_id: 'coll-1',
            mode: 'normal',
            filters: { sample_ids: ['id-1'] }
        });

        const { isVisible, effectiveCount, setVisibility } = useEmbeddingFilterForImages(
            collectionId,
            setRangeSelection
        );
        setVisibility(false);

        updateFilterParams({
            collection_id: 'coll-1',
            mode: 'classifier'
        });
        setVisibility(true);

        expect(get(isVisible)).toBe(false);
        expect(get(effectiveCount)).toBe(1);
    });

    it('setVisibility(false) does nothing when there are no active IDs', () => {
        const { effectiveCount, setVisibility } = useEmbeddingFilterForImages(
            collectionId,
            setRangeSelection
        );
        setVisibility(false);
        expect(get(effectiveCount)).toBe(0);
    });

    it('clearFilter clears both active and hidden IDs and calls setRangeSelection', () => {
        const { updateFilterParams } = useImageFilters();
        updateFilterParams({
            collection_id: 'coll-1',
            mode: 'normal',
            filters: { sample_ids: ['id-1'] }
        });

        const { effectiveCount, setVisibility, clearFilter } = useEmbeddingFilterForImages(
            collectionId,
            setRangeSelection
        );
        setVisibility(false);
        clearFilter();

        expect(get(effectiveCount)).toBe(0);
        expect(setRangeSelection).toHaveBeenCalledWith('coll-1', null);
    });
});

describe('useEmbeddingFilterForVideos', () => {
    const collectionId = writable('coll-1');
    const setRangeSelection = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        const { updateFilterParams } = useVideoFilters();
        updateFilterParams(null as unknown as Parameters<typeof updateFilterParams>[0]);
        const { clearHidden } = useHiddenFilters(collectionId);
        clearHidden();
    });

    it('isVisible is false when collection_id does not match', () => {
        const { updateFilterParams } = useVideoFilters();
        updateFilterParams({ collection_id: 'other-coll', filters: { sample_ids: ['id-1'] } });

        const { isVisible } = useEmbeddingFilterForVideos(collectionId, setRangeSelection);
        expect(get(isVisible)).toBe(false);
    });

    it('isVisible is true when collection matches and sample_ids are set', () => {
        const { updateFilterParams } = useVideoFilters();
        updateFilterParams({
            collection_id: 'coll-1',
            filters: { sample_ids: ['id-1', 'id-2'] }
        });

        const { isVisible, effectiveCount } = useEmbeddingFilterForVideos(
            collectionId,
            setRangeSelection
        );
        expect(get(isVisible)).toBe(true);
        expect(get(effectiveCount)).toBe(2);
    });

    it('setVisibility(false) moves active IDs to hidden and clears the filter', () => {
        const { updateFilterParams } = useVideoFilters();
        updateFilterParams({
            collection_id: 'coll-1',
            filters: { sample_ids: ['id-1', 'id-2'] }
        });

        const { isVisible, effectiveCount, setVisibility } = useEmbeddingFilterForVideos(
            collectionId,
            setRangeSelection
        );
        setVisibility(false);

        expect(get(isVisible)).toBe(false);
        expect(get(effectiveCount)).toBe(2);
    });

    it('setVisibility(true) restores previously hidden IDs', () => {
        const { updateFilterParams } = useVideoFilters();
        updateFilterParams({
            collection_id: 'coll-1',
            filters: { sample_ids: ['id-1', 'id-2'] }
        });

        const { isVisible, effectiveCount, setVisibility } = useEmbeddingFilterForVideos(
            collectionId,
            setRangeSelection
        );
        setVisibility(false);
        setVisibility(true);

        expect(get(isVisible)).toBe(true);
        expect(get(effectiveCount)).toBe(2);
    });

    it('setVisibility(false) does nothing when there are no active IDs', () => {
        const { effectiveCount, setVisibility } = useEmbeddingFilterForVideos(
            collectionId,
            setRangeSelection
        );
        setVisibility(false);
        expect(get(effectiveCount)).toBe(0);
    });

    it('clearFilter clears both active and hidden IDs and calls setRangeSelection', () => {
        const { updateFilterParams } = useVideoFilters();
        updateFilterParams({ collection_id: 'coll-1', filters: { sample_ids: ['id-1'] } });

        const { effectiveCount, setVisibility, clearFilter } = useEmbeddingFilterForVideos(
            collectionId,
            setRangeSelection
        );
        setVisibility(false);
        clearFilter();

        expect(get(effectiveCount)).toBe(0);
        expect(setRangeSelection).toHaveBeenCalledWith('coll-1', null);
    });
});
