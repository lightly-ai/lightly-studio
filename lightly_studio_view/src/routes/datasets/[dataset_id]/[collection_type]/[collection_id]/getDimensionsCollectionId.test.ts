import { SampleType } from '$lib/api/lightly_studio_local/types.gen';
import { getDimensionsCollectionId } from './getDimensionsCollectionId';

describe('getDimensionsCollectionId', () => {
    it('uses the image collection for image and image-annotation views only', () => {
        expect(
            getDimensionsCollectionId({
                collectionId: 'images',
                collectionSampleType: SampleType.IMAGE,
                parentCollection: null
            })
        ).toBe('images');
        expect(
            getDimensionsCollectionId({
                collectionId: 'annotations',
                collectionSampleType: SampleType.ANNOTATION,
                parentCollection: {
                    collectionId: 'images',
                    sampleType: SampleType.IMAGE
                }
            })
        ).toBe('images');
        expect(
            getDimensionsCollectionId({
                collectionId: 'annotations',
                collectionSampleType: SampleType.ANNOTATION,
                parentCollection: {
                    collectionId: 'frames',
                    sampleType: SampleType.VIDEO_FRAME
                }
            })
        ).toBeUndefined();
    });

    it('uses the parent image collection for caption views', () => {
        expect(
            getDimensionsCollectionId({
                collectionId: 'captions',
                collectionSampleType: SampleType.CAPTION,
                parentCollection: {
                    collectionId: 'images',
                    sampleType: SampleType.IMAGE
                }
            })
        ).toBe('images');
        expect(
            getDimensionsCollectionId({
                collectionId: 'captions',
                collectionSampleType: SampleType.CAPTION,
                parentCollection: {
                    collectionId: 'frames',
                    sampleType: SampleType.VIDEO_FRAME
                }
            })
        ).toBeUndefined();
    });
});
