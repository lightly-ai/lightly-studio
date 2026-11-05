import { describe, expect, it } from 'vitest';
import { getAnnotationClassId, setAnnotationClasses } from '$lib/hooks/useCustomLabelColors';

const makeClass = (id: string, name: string, datasetId: string) => ({
    annotation_label_id: id,
    annotation_label_name: name,
    dataset_id: datasetId,
    color: null,
    alpha: null
});

describe('annotation class IDs', () => {
    it('setAnnotationClasses maps names to IDs', () => {
        setAnnotationClasses('dataset-a', [makeClass('id-1', 'cat', 'dataset-a')]);

        expect(getAnnotationClassId('cat')).toBe('id-1');
        expect(getAnnotationClassId('dog')).toBeUndefined();
    });

    it('setAnnotationClasses ignores classes of another dataset', () => {
        setAnnotationClasses('dataset-b', [
            makeClass('id-1', 'cat', 'dataset-b'),
            makeClass('id-2', 'dog', 'dataset-other')
        ]);

        expect(getAnnotationClassId('cat')).toBe('id-1');
        expect(getAnnotationClassId('dog')).toBeUndefined();
    });

    it('setAnnotationClasses with stale classes of another dataset clears the class IDs', () => {
        setAnnotationClasses('dataset-c', [makeClass('id-1', 'cat', 'dataset-c')]);

        setAnnotationClasses('dataset-d', [makeClass('id-1', 'cat', 'dataset-c')]);

        expect(getAnnotationClassId('cat')).toBeUndefined();
    });
});
