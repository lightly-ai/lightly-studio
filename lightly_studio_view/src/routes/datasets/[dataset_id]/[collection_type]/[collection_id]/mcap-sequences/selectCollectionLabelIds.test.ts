import { describe, expect, it } from 'vitest';
import { selectCollectionLabelIds } from './selectCollectionLabelIds';

describe('selectCollectionLabelIds', () => {
    it('drops the selected labels that the collection does not have', () => {
        expect(
            selectCollectionLabelIds({
                selectedLabelIds: ['car-id', 'other-dataset-id'],
                collectionLabelIds: ['car-id', 'person-id']
            })
        ).toEqual(['car-id']);
    });

    it('keeps the selection while the labels of the collection load', () => {
        expect(
            selectCollectionLabelIds({
                selectedLabelIds: ['car-id'],
                collectionLabelIds: undefined
            })
        ).toEqual(['car-id']);
    });
});
