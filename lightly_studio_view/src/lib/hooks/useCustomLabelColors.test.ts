import { describe, expect, it } from 'vitest';
import {
    getAnnotationClassId,
    resetAnnotationClasses,
    setAnnotationClasses
} from '$lib/hooks/useCustomLabelColors';

const makeClass = (id: string, name: string, datasetId: string) => ({
    annotation_label_id: id,
    annotation_label_name: name,
    dataset_id: datasetId,
    color: null,
    alpha: null
});

describe('annotation class IDs', () => {
    it('setAnnotationClasses maps names to IDs', () => {
        resetAnnotationClasses('dataset-a');
        setAnnotationClasses('dataset-a', [makeClass('id-1', 'cat', 'dataset-a')]);

        expect(getAnnotationClassId('cat')).toBe('id-1');
        expect(getAnnotationClassId('dog')).toBeUndefined();
    });

    it('resetAnnotationClasses to another dataset clears the class IDs', () => {
        resetAnnotationClasses('dataset-b');
        setAnnotationClasses('dataset-b', [makeClass('id-1', 'cat', 'dataset-b')]);

        resetAnnotationClasses('dataset-c');

        expect(getAnnotationClassId('cat')).toBeUndefined();
    });

    it('setAnnotationClasses ignores classes of another dataset', () => {
        resetAnnotationClasses('dataset-d');

        setAnnotationClasses('dataset-other', [makeClass('id-1', 'cat', 'dataset-other')]);
        setAnnotationClasses('dataset-d', [
            makeClass('id-2', 'dog', 'dataset-d'),
            makeClass('id-3', 'bird', 'dataset-other')
        ]);

        expect(getAnnotationClassId('cat')).toBeUndefined();
        expect(getAnnotationClassId('dog')).toBe('id-2');
        expect(getAnnotationClassId('bird')).toBeUndefined();
    });
});
