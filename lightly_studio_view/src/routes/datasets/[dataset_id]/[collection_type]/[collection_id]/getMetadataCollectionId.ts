import {
    SampleType,
    type SampleType as SampleTypeValue
} from '$lib/api/lightly_studio_local/types.gen';

interface ParentCollection {
    collectionId: string;
}

interface GetMetadataCollectionIdParams {
    collectionId: string;
    collectionSampleType: SampleTypeValue;
    parentCollection: ParentCollection | null;
}

export const getMetadataCollectionId = ({
    collectionId,
    collectionSampleType,
    parentCollection
}: GetMetadataCollectionIdParams): string => {
    if (collectionSampleType === SampleType.ANNOTATION && parentCollection) {
        return parentCollection.collectionId;
    }
    return collectionId;
};
