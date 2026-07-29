import {
    SampleType,
    type SampleType as SampleTypeValue
} from '$lib/api/lightly_studio_local/types.gen';

interface ParentCollection {
    collectionId: string;
    sampleType: SampleTypeValue;
}

interface GetDimensionsCollectionIdParams {
    collectionId: string;
    collectionSampleType: SampleTypeValue;
    parentCollection: ParentCollection | null;
}

export const getDimensionsCollectionId = ({
    collectionId,
    collectionSampleType,
    parentCollection
}: GetDimensionsCollectionIdParams): string | undefined => {
    if (collectionSampleType === SampleType.IMAGE) return collectionId;
    if (
        (collectionSampleType === SampleType.ANNOTATION ||
            collectionSampleType === SampleType.CAPTION) &&
        parentCollection?.sampleType === SampleType.IMAGE
    ) {
        return parentCollection.collectionId;
    }
    return undefined;
};
