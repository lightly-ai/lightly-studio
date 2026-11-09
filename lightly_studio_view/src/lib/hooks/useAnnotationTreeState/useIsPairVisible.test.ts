import { get } from 'svelte/store';
import { describe, expect, it } from 'vitest';
import { useAnnotationTreeState } from './useAnnotationTreeState';
import { toIsAnnotationVisible, useIsPairVisible } from './useIsPairVisible';

const annotation = (sourceId: string, labelName: string) => ({
    annotation_collection_id: sourceId,
    annotation_label: { annotation_label_name: labelName }
});

const labels = [
    { dataset_id: 'd', annotation_label_id: 'lbl-car', annotation_label_name: 'car' },
    { dataset_id: 'd', annotation_label_id: 'lbl-person', annotation_label_name: 'person' }
];

describe('useIsPairVisible', () => {
    it('hides only the hidden pair of the collection', () => {
        useAnnotationTreeState('pairs-1').setVisible(
            [{ collection_id: 'labels', annotation_label_id: 'lbl-car' }],
            false
        );

        const isPairVisible = get(useIsPairVisible('pairs-1'));

        expect(isPairVisible('labels', 'lbl-car')).toBe(false);
        expect(isPairVisible('model_v1', 'lbl-car')).toBe(true);
        expect(isPairVisible('labels', 'lbl-person')).toBe(true);
        expect(get(useIsPairVisible('pairs-2'))('labels', 'lbl-car')).toBe(true);
    });
});

describe('toIsAnnotationVisible', () => {
    it('looks up the class id by name and keeps unknown classes visible', () => {
        const isVisible = toIsAnnotationVisible(
            (sourceId, labelId) => !(sourceId === 'labels' && labelId === 'lbl-car'),
            labels
        );

        expect(isVisible(annotation('labels', 'car'))).toBe(false);
        expect(isVisible(annotation('model_v1', 'car'))).toBe(true);
        expect(isVisible(annotation('labels', 'person'))).toBe(true);
        expect(isVisible(annotation('labels', 'unknown'))).toBe(true);
    });
});
