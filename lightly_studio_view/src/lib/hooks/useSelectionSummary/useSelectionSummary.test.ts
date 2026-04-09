import { get } from 'svelte/store';
import { beforeEach, describe, expect, it } from 'vitest';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { useSelectionSummary } from './useSelectionSummary';

describe('useSelectionSummary', () => {
    const collectionId = 'test-collection';
    let storage: ReturnType<typeof useGlobalStorage>;

    beforeEach(() => {
        storage = useGlobalStorage();
        storage.clearSelectedSamples(collectionId);
        storage.clearSelectedSampleAnnotationCrops(collectionId);
    });

    it('returns zero when nothing is selected', () => {
        const { selectedCount } = useSelectionSummary(collectionId);
        expect(get(selectedCount)).toBe(0);
    });

    it('counts selected samples', () => {
        storage.toggleSampleSelection('s1', collectionId);
        storage.toggleSampleSelection('s2', collectionId);

        const { selectedCount } = useSelectionSummary(collectionId);
        expect(get(selectedCount)).toBe(2);
    });

    it('counts selected annotation crops', () => {
        storage.toggleSampleAnnotationCropSelection(collectionId, 'a1');

        const { selectedCount } = useSelectionSummary(collectionId);
        expect(get(selectedCount)).toBe(1);
    });

    it('sums samples and annotation crops', () => {
        storage.toggleSampleSelection('s1', collectionId);
        storage.toggleSampleAnnotationCropSelection(collectionId, 'a1');
        storage.toggleSampleAnnotationCropSelection(collectionId, 'a2');

        const { selectedCount } = useSelectionSummary(collectionId);
        expect(get(selectedCount)).toBe(3);
    });

    it('clearSelection resets the count to zero', () => {
        storage.toggleSampleSelection('s1', collectionId);
        storage.toggleSampleAnnotationCropSelection(collectionId, 'a1');

        const { selectedCount, clearSelection } = useSelectionSummary(collectionId);
        expect(get(selectedCount)).toBe(2);

        clearSelection();
        expect(get(selectedCount)).toBe(0);
    });
});
