import { get } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useGlobalStorage } from './useGlobalStorage';

describe('useGlobalStorage', () => {
    let storage: ReturnType<typeof useGlobalStorage>;
    const testCollectionId = 'test-collection-1';
    const testCollectionId2 = 'test-collection-2';

    beforeEach(() => {
        storage = useGlobalStorage();
        // Clear all selections before each test
        storage.clearSelectedSamples(testCollectionId);
        storage.clearSelectedSampleAnnotationCrops(testCollectionId);

        storage.clearSelectedSamples(testCollectionId2);
        storage.clearSelectedSampleAnnotationCrops(testCollectionId2);
    });

    describe('Sample selection', () => {
        it('should select a sample', () => {
            storage.toggleSampleSelection('sample1', testCollectionId);
            const selectedSampleIds = storage.getSelectedSampleIds(testCollectionId);
            expect(get(selectedSampleIds).has('sample1')).toBe(true);
        });

        it('should unselect a sample', () => {
            storage.toggleSampleSelection('sample1', testCollectionId);
            storage.toggleSampleSelection('sample1', testCollectionId);
            const selectedSampleIds = storage.getSelectedSampleIds(testCollectionId);
            expect(get(selectedSampleIds).has('sample1')).toBe(false);
        });

        it('should clear all selected samples', () => {
            storage.toggleSampleSelection('sample1', testCollectionId);
            storage.toggleSampleSelection('sample2', testCollectionId);
            storage.clearSelectedSamples(testCollectionId);
            const selectedSampleIds = storage.getSelectedSampleIds(testCollectionId);
            expect(get(selectedSampleIds).size).toBe(0);
        });
    });

    describe('Annotation selection', () => {
        it('should select an annotation', () => {
            storage.toggleSampleAnnotationCropSelection(testCollectionId, 'annotation1');
            expect(
                get(storage.selectedSampleAnnotationCropIds)[testCollectionId].has('annotation1')
            ).toBe(true);
        });

        it('should select an annotation from a specific collection', () => {
            storage.toggleSampleAnnotationCropSelection(testCollectionId, 'annotation1');
            storage.toggleSampleAnnotationCropSelection(testCollectionId2, 'annotation2');

            expect(
                get(storage.selectedSampleAnnotationCropIds)[testCollectionId2].has('annotation2')
            ).toBe(true);
            expect(
                get(storage.selectedSampleAnnotationCropIds)[testCollectionId2].has('annotation2')
            ).toBe(true);
        });

        it('should unselect an annotation', () => {
            storage.toggleSampleAnnotationCropSelection(testCollectionId, 'annotation1');
            storage.toggleSampleAnnotationCropSelection(testCollectionId, 'annotation1');
            expect(
                get(storage.selectedSampleAnnotationCropIds)[testCollectionId].has('annotation1')
            ).toBe(false);
        });

        it('should unselect an annotation from a specific collection', () => {
            storage.toggleSampleAnnotationCropSelection(testCollectionId, 'annotation1');

            storage.toggleSampleAnnotationCropSelection(testCollectionId2, 'annotation2');
            storage.toggleSampleAnnotationCropSelection(testCollectionId2, 'annotation2');

            expect(
                get(storage.selectedSampleAnnotationCropIds)[testCollectionId].has('annotation1')
            ).toBe(true);
            expect(
                get(storage.selectedSampleAnnotationCropIds)[testCollectionId2].has('annotation2')
            ).toBe(false);
        });

        it('should clear all selected annotations', () => {
            storage.toggleSampleAnnotationCropSelection(testCollectionId, 'annotation1');
            storage.toggleSampleAnnotationCropSelection(testCollectionId, 'annotation2');
            storage.clearSelectedSampleAnnotationCrops(testCollectionId);
            expect(get(storage.selectedSampleAnnotationCropIds)[testCollectionId].size).toBe(0);
        });

        it('should clear all selected annotations from a specific collection', () => {
            storage.toggleSampleAnnotationCropSelection(testCollectionId, 'annotation1');
            storage.toggleSampleAnnotationCropSelection(testCollectionId, 'annotation2');

            storage.toggleSampleAnnotationCropSelection(testCollectionId2, 'annotation1');
            storage.toggleSampleAnnotationCropSelection(testCollectionId2, 'annotation2');
            storage.clearSelectedSampleAnnotationCrops(testCollectionId2);

            expect(get(storage.selectedSampleAnnotationCropIds)[testCollectionId].size).toBe(2);
            expect(get(storage.selectedSampleAnnotationCropIds)[testCollectionId2].size).toBe(0);
        });
    });

    describe('Store independence', () => {
        it('should maintain separate states for samples and annotations', () => {
            storage.toggleSampleSelection('sample1', testCollectionId);
            storage.toggleSampleAnnotationCropSelection(testCollectionId, 'annotation1');

            // Modify samples shouldn't affect annotations
            storage.clearSelectedSamples(testCollectionId);
            const selectedSampleIds = storage.getSelectedSampleIds(testCollectionId);
            expect(get(selectedSampleIds).size).toBe(0);
            expect(
                get(storage.selectedSampleAnnotationCropIds)[testCollectionId].has('annotation1')
            ).toBe(true);

            // Modify annotations shouldn't affect samples
            storage.toggleSampleSelection('sample2', testCollectionId);
            storage.clearSelectedSampleAnnotationCrops(testCollectionId);
            expect(get(selectedSampleIds).has('sample2')).toBe(true);
            expect(get(storage.selectedSampleAnnotationCropIds)[testCollectionId].size).toBe(0);
        });

        it('should only trigger subscribers for the modified store', () => {
            const sampleSubscriber = vi.fn();
            const annotationSubscriber = vi.fn();

            // Subscribe to both stores
            const selectedSampleIds = storage.getSelectedSampleIds(testCollectionId);
            selectedSampleIds.subscribe(sampleSubscriber);
            storage.selectedSampleAnnotationCropIds.subscribe(annotationSubscriber);

            // Reset mock call counts
            sampleSubscriber.mockClear();
            annotationSubscriber.mockClear();

            // Modify only samples
            storage.toggleSampleSelection('sample1', testCollectionId);
            expect(sampleSubscriber).toHaveBeenCalled();
            expect(annotationSubscriber).not.toHaveBeenCalled();

            // Reset mock call counts
            sampleSubscriber.mockClear();
            annotationSubscriber.mockClear();

            // Modify only annotations
            storage.toggleSampleAnnotationCropSelection(testCollectionId, 'annotation1');
            expect(sampleSubscriber).not.toHaveBeenCalled();
            expect(annotationSubscriber).toHaveBeenCalled();
        });

        it('should maintain separate selections for different collections', () => {
            const collection1 = 'collection-1';
            const collection2 = 'collection-2';
            const storage1 = useGlobalStorage();
            const storage2 = useGlobalStorage();

            storage1.toggleSampleSelection('sample1', collection1);
            storage2.toggleSampleSelection('sample2', collection2);

            // Each collection should have its own selection
            const selected1 = storage1.getSelectedSampleIds(collection1);
            const selected2 = storage2.getSelectedSampleIds(collection2);
            expect(get(selected1).has('sample1')).toBe(true);
            expect(get(selected1).has('sample2')).toBe(false);
            expect(get(selected2).has('sample1')).toBe(false);
            expect(get(selected2).has('sample2')).toBe(true);
        });
    });

    describe('Text Embedding', () => {
        it('should store value', () => {
            storage.setTextEmbedding({
                queryText: 'text',
                embedding: [1, 2, 3]
            });
            const storedValue = get(storage.textEmbedding);
            // Check the exact value of queryText
            expect(storedValue?.queryText).toBe('text');
            // Check the embedding array
            expect(storedValue?.embedding).toEqual([1, 2, 3]);
        });
    });

    describe('Editing mode', () => {
        it('should propagate setIsEditingMode value to isEditingMode', () => {
            // Initially should be false
            expect(get(storage.isEditingMode)).toBeFalsy();

            // Set to true
            storage.setIsEditingMode(true);
            expect(get(storage.isEditingMode)).toBe(true);

            // Set to false
            storage.setIsEditingMode(false);
            expect(get(storage.isEditingMode)).toBe(false);
        });

        it('should trigger subscribers when isEditingMode changes', () => {
            const subscriber = vi.fn();
            storage.isEditingMode.subscribe(subscriber);

            // Reset mock call count (initial subscription call)
            subscriber.mockClear();

            // Change editing mode
            storage.setIsEditingMode(true);
            expect(subscriber).toHaveBeenCalledWith(true);

            // Change again
            storage.setIsEditingMode(false);
            expect(subscriber).toHaveBeenCalledWith(false);
        });
    });
});
