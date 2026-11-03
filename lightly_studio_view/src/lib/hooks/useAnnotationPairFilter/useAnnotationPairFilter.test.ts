import { get } from 'svelte/store';
import { beforeEach, describe, expect, it } from 'vitest';
import { getAnnotationsFilter } from '$lib/hooks/useImagesInfinite/getAnnotationsFilter';
import { useAnnotationPairFilter } from './useAnnotationPairFilter';

const IMAGES = 'images-collection';
const ANNOTATIONS = 'annotations-collection';

describe('useAnnotationPairFilter', () => {
    beforeEach(() => {
        useAnnotationPairFilter(IMAGES).clear();
        useAnnotationPairFilter(ANNOTATIONS).clear();
    });

    it('toggles one pair on and off', () => {
        const { pairs, togglePair } = useAnnotationPairFilter(IMAGES);

        togglePair('ground_truth', 'deer');
        togglePair('model_v1', 'raccoon');
        expect(get(pairs)).toEqual([
            { collection_id: 'ground_truth', annotation_label_id: 'deer' },
            { collection_id: 'model_v1', annotation_label_id: 'raccoon' }
        ]);

        togglePair('ground_truth', 'deer');
        expect(get(pairs)).toEqual([{ collection_id: 'model_v1', annotation_label_id: 'raccoon' }]);
    });

    it('sets and unsets every class of a source', () => {
        const { pairs, setSource } = useAnnotationPairFilter(IMAGES);

        setSource('ground_truth', ['deer', 'raccoon'], true);
        expect(get(pairs)).toEqual([
            { collection_id: 'ground_truth', annotation_label_id: 'deer' },
            { collection_id: 'ground_truth', annotation_label_id: 'raccoon' }
        ]);

        setSource('ground_truth', ['deer', 'raccoon'], false);
        expect(get(pairs)).toEqual([]);
    });

    it('reports a source as checked, partial or unchecked', () => {
        const { sourceState, togglePair } = useAnnotationPairFilter(IMAGES);
        const labelIds = ['deer', 'raccoon'];

        expect(sourceState('ground_truth', labelIds)).toBe('unchecked');
        togglePair('ground_truth', 'deer');
        expect(sourceState('ground_truth', labelIds)).toBe('partial');
        // A deer in another source does not tick ground_truth's classes.
        togglePair('model_v1', 'raccoon');
        expect(sourceState('ground_truth', labelIds)).toBe('partial');
        togglePair('ground_truth', 'raccoon');
        expect(sourceState('ground_truth', labelIds)).toBe('checked');
    });

    it('sends no source_label_pairs while nothing is ticked', () => {
        const { pairs, togglePair } = useAnnotationPairFilter(IMAGES);
        expect(getAnnotationsFilter({ source_label_pairs: get(pairs) })).toBeUndefined();

        togglePair('ground_truth', 'deer');
        expect(getAnnotationsFilter({ source_label_pairs: get(pairs) })).toEqual({
            filter_type: 'annotations',
            source_label_pairs: [{ collection_id: 'ground_truth', annotation_label_id: 'deer' }]
        });
    });

    it('keeps the pairs of each tab across a switch to the annotations tab and back', () => {
        useAnnotationPairFilter(IMAGES).togglePair('ground_truth', 'deer');

        const annotationsTab = useAnnotationPairFilter(ANNOTATIONS);
        expect(get(annotationsTab.pairs)).toEqual([]);
        annotationsTab.togglePair(ANNOTATIONS, 'raccoon');

        expect(get(useAnnotationPairFilter(IMAGES).pairs)).toEqual([
            { collection_id: 'ground_truth', annotation_label_id: 'deer' }
        ]);
        expect(get(useAnnotationPairFilter(ANNOTATIONS).pairs)).toEqual([
            { collection_id: ANNOTATIONS, annotation_label_id: 'raccoon' }
        ]);
    });

    it('drops every pair of one source', () => {
        const { pairs, togglePair, dropSource } = useAnnotationPairFilter(IMAGES);
        togglePair('ground_truth', 'deer');
        togglePair('model_v1', 'deer');

        dropSource('model_v1');

        expect(get(pairs)).toEqual([
            { collection_id: 'ground_truth', annotation_label_id: 'deer' }
        ]);
    });
});
