import { describe, expect, it } from 'vitest';
import {
    getAnnotationClassId,
    useCustomLabelColors,
    resetAnnotationClasses,
    setAnnotationClasses
} from '$lib/hooks/useCustomLabelColors';

const makeClass = (
    id: string,
    name: string,
    datasetId: string,
    color: string | null = null,
    alpha: number | null = null
) => ({
    annotation_label_id: id,
    annotation_label_name: name,
    dataset_id: datasetId,
    color,
    alpha
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

describe('annotation class colors', () => {
    const { getCustomColor, setPreviewColor } = useCustomLabelColors();

    it('loads saved colors', () => {
        resetAnnotationClasses('ds-colors-1');

        setAnnotationClasses('ds-colors-1', [
            makeClass('id-1', 'cat', 'ds-colors-1', '#ff0000', 0.5),
            makeClass('id-2', 'dog', 'ds-colors-1'),
            makeClass('id-3', 'bird', 'ds-colors-1', '#00ff00')
        ]);

        expect(getCustomColor('cat')).toEqual({ color: '#ff0000', alpha: 0.5 });
        expect(getCustomColor('dog')).toBeUndefined();
        expect(getCustomColor('bird')).toEqual({ color: '#00ff00', alpha: 1 });
    });

    it('a reload without colors clears the saved colors', () => {
        resetAnnotationClasses('ds-colors-2');
        setAnnotationClasses('ds-colors-2', [makeClass('id-1', 'cat', 'ds-colors-2', '#ff0000')]);

        setAnnotationClasses('ds-colors-2', [makeClass('id-1', 'cat', 'ds-colors-2')]);

        expect(getCustomColor('cat')).toBeUndefined();
    });

    it('replaces the previous classes', () => {
        resetAnnotationClasses('ds-colors-3');
        setAnnotationClasses('ds-colors-3', [makeClass('id-1', 'cat', 'ds-colors-3', '#ff0000')]);

        setAnnotationClasses('ds-colors-3', [makeClass('id-1', 'kitty', 'ds-colors-3', '#ff0000')]);

        expect(getCustomColor('cat')).toBeUndefined();
        expect(getCustomColor('kitty')?.color).toBe('#ff0000');
    });

    it('a refetch of the same dataset keeps an open preview', () => {
        resetAnnotationClasses('ds-1');
        setAnnotationClasses('ds-1', [makeClass('id-1', 'cat', 'ds-1')]);
        const owner = Symbol();
        setPreviewColor('cat', { color: '#abcdef', alpha: 1 }, owner);

        resetAnnotationClasses('ds-1');
        setAnnotationClasses('ds-1', [makeClass('id-1', 'cat', 'ds-1', '#112233')]);

        expect(getCustomColor('cat')?.color).toBe('#abcdef');
    });

    it('switching datasets drops previews and colors', () => {
        resetAnnotationClasses('ds-1');
        setAnnotationClasses('ds-1', [makeClass('id-1', 'cat', 'ds-1', '#112233')]);
        setPreviewColor('cat', { color: '#abcdef', alpha: 1 }, Symbol());

        resetAnnotationClasses('ds-2');

        expect(getCustomColor('cat')).toBeUndefined();
    });
});
