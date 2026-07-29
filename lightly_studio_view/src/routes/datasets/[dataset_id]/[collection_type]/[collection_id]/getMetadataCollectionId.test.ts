import { SampleType } from '$lib/api/lightly_studio_local/types.gen';
import { getMetadataCollectionId } from './getMetadataCollectionId';

describe('getMetadataCollectionId', () => {
    it('uses the current collection for sample views', () => {
        expect(
            getMetadataCollectionId({
                collectionId: 'images',
                collectionSampleType: SampleType.IMAGE,
                parentCollection: null
            })
        ).toBe('images');
    });

    it('uses the parent sample collection for annotation views', () => {
        expect(
            getMetadataCollectionId({
                collectionId: 'annotations',
                collectionSampleType: SampleType.ANNOTATION,
                parentCollection: { collectionId: 'images' }
            })
        ).toBe('images');
    });

    it('falls back to the annotation collection when no parent is available', () => {
        expect(
            getMetadataCollectionId({
                collectionId: 'annotations',
                collectionSampleType: SampleType.ANNOTATION,
                parentCollection: null
            })
        ).toBe('annotations');
    });

    it('uses the parent sample collection for caption views', () => {
        expect(
            getMetadataCollectionId({
                collectionId: 'captions',
                collectionSampleType: SampleType.CAPTION,
                parentCollection: { collectionId: 'images' }
            })
        ).toBe('images');
    });

    it('falls back to the caption collection when no parent is available', () => {
        expect(
            getMetadataCollectionId({
                collectionId: 'captions',
                collectionSampleType: SampleType.CAPTION,
                parentCollection: null
            })
        ).toBe('captions');
    });
});
