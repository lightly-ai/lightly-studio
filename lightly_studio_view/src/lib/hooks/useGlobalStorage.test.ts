import { get } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useGlobalStorage } from './useGlobalStorage';

describe('useGlobalStorage', () => {
    let storage: ReturnType<typeof useGlobalStorage>;
    const testDatasetId = 'test-dataset-1';

    beforeEach(() => {
        storage = useGlobalStorage();
        // Clear all selections before each test
        storage.clearSelectedSamples(testDatasetId);
        storage.clearSelectedSampleAnnotationCrops();
    });

    describe('Sample selection', () => {
        it('should select a sample', () => {
            storage.toggleSampleSelection('sample1', testDatasetId);
            const selectedSampleIds = storage.getSelectedSampleIds(testDatasetId);
            expect(get(selectedSampleIds).has('sample1')).toBe(true);
        });

        it('should unselect a sample', () => {
            storage.toggleSampleSelection('sample1', testDatasetId);
            storage.toggleSampleSelection('sample1', testDatasetId);
            const selectedSampleIds = storage.getSelectedSampleIds(testDatasetId);
            expect(get(selectedSampleIds).has('sample1')).toBe(false);
        });

        it('should clear all selected samples', () => {
            storage.toggleSampleSelection('sample1', testDatasetId);
            storage.toggleSampleSelection('sample2', testDatasetId);
            storage.clearSelectedSamples(testDatasetId);
            const selectedSampleIds = storage.getSelectedSampleIds(testDatasetId);
            expect(get(selectedSampleIds).size).toBe(0);
        });
    });

    describe('Annotation selection', () => {
        it('should select an annotation', () => {
            storage.toggleSampleAnnotationCropSelection('annotation1');
            expect(get(storage.selectedSampleAnnotationCropIds).has('annotation1')).toBe(true);
        });

        it('should unselect an annotation', () => {
            storage.toggleSampleAnnotationCropSelection('annotation1');
            storage.toggleSampleAnnotationCropSelection('annotation1');
            expect(get(storage.selectedSampleAnnotationCropIds).has('annotation1')).toBe(false);
        });

        it('should clear all selected annotations', () => {
            storage.toggleSampleAnnotationCropSelection('annotation1');
            storage.toggleSampleAnnotationCropSelection('annotation2');
            storage.clearSelectedSampleAnnotationCrops();
            expect(get(storage.selectedSampleAnnotationCropIds).size).toBe(0);
        });
    });

    describe('Store independence', () => {
        it('should maintain separate states for samples and annotations', () => {
            storage.toggleSampleSelection('sample1', testDatasetId);
            storage.toggleSampleAnnotationCropSelection('annotation1');

            // Modify samples shouldn't affect annotations
            storage.clearSelectedSamples(testDatasetId);
            const selectedSampleIds = storage.getSelectedSampleIds(testDatasetId);
            expect(get(selectedSampleIds).size).toBe(0);
            expect(get(storage.selectedSampleAnnotationCropIds).has('annotation1')).toBe(true);

            // Modify annotations shouldn't affect samples
            storage.toggleSampleSelection('sample2', testDatasetId);
            storage.clearSelectedSampleAnnotationCrops();
            expect(get(selectedSampleIds).has('sample2')).toBe(true);
            expect(get(storage.selectedSampleAnnotationCropIds).size).toBe(0);
        });

        it('should only trigger subscribers for the modified store', () => {
            const sampleSubscriber = vi.fn();
            const annotationSubscriber = vi.fn();

            // Subscribe to both stores
            const selectedSampleIds = storage.getSelectedSampleIds(testDatasetId);
            selectedSampleIds.subscribe(sampleSubscriber);
            storage.selectedSampleAnnotationCropIds.subscribe(annotationSubscriber);

            // Reset mock call counts
            sampleSubscriber.mockClear();
            annotationSubscriber.mockClear();

            // Modify only samples
            storage.toggleSampleSelection('sample1', testDatasetId);
            expect(sampleSubscriber).toHaveBeenCalled();
            expect(annotationSubscriber).not.toHaveBeenCalled();

            // Reset mock call counts
            sampleSubscriber.mockClear();
            annotationSubscriber.mockClear();

            // Modify only annotations
            storage.toggleSampleAnnotationCropSelection('annotation1');
            expect(sampleSubscriber).not.toHaveBeenCalled();
            expect(annotationSubscriber).toHaveBeenCalled();
        });

        it('should maintain separate selections for different datasets', () => {
            const dataset1 = 'dataset-1';
            const dataset2 = 'dataset-2';
            const storage1 = useGlobalStorage();
            const storage2 = useGlobalStorage();

            storage1.toggleSampleSelection('sample1', dataset1);
            storage2.toggleSampleSelection('sample2', dataset2);

            // Each dataset should have its own selection
            const selected1 = storage1.getSelectedSampleIds(dataset1);
            const selected2 = storage2.getSelectedSampleIds(dataset2);
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
