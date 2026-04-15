import { goto } from '$app/navigation';
import type { CollectionView, CollectionViewWithCount } from '$lib/api/lightly_studio_local';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { routeHelpers } from '$lib/routes';
import { fetchCollection, fetchCollectionHierarchy } from '$lib/utils';
import { validate as validateUUID } from 'uuid';

import type { LayoutLoad, LayoutLoadEvent } from './$types';

export type LayoutLoadResult = {
    collection: CollectionViewWithCount;
    collectionHierarchy: CollectionView[];
    globalStorage: ReturnType<typeof useGlobalStorage>;
    sampleSize: ReturnType<typeof useGlobalStorage>['sampleSize'];
};

export const load: LayoutLoad = async ({
    params: { dataset_id, collection_type, collection_id }
}: LayoutLoadEvent): Promise<LayoutLoadResult> => {
    // If we have some invalid params, we should just redirect to the home page
    if (!validateUUID(dataset_id) || !validateUUID(collection_id)) {
        goto(routeHelpers.toHome());
        return new Promise(() => {}); // Return a never-resolving promise to prevent further execution
    }

    const collectionData = await fetchCollection(collection_id);

    // If collection type does not match the sample type
    if (collectionData.sample_type.toLowerCase() !== collection_type.toLowerCase()) {
        goto(
            routeHelpers.toCollectionHome(
                dataset_id,
                collectionData.sample_type.toLowerCase(),
                collection_id
            )
        );
        return new Promise(() => {}); // Return a never-resolving promise to prevent further execution
    }

    let collectionHierarchy: CollectionView[] = [];

    if (collection_id !== dataset_id) {
        const hierarchy = await fetchCollectionHierarchy(dataset_id);

        if (!hierarchy.some((collection) => collection.collection_id === collection_id)) {
            throw new Error(`Collection ${collection_id} does not belong to dataset ${dataset_id}`);
        }
        collectionHierarchy = hierarchy;
    }

    const globalStorage = useGlobalStorage();

    return {
        collection: collectionData,
        collectionHierarchy,
        globalStorage,
        sampleSize: globalStorage.sampleSize
    };
};
