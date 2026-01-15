import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import type { LayoutLoad, LayoutLoadEvent } from './$types';
import { readCollection, readDataset } from '$lib/api/lightly_studio_local/sdk.gen';
import { routeHelpers } from '$lib/routes';
import { redirect } from '@sveltejs/kit';
import { derived, type Readable } from 'svelte/store';

export type LayoutLoadResult = {
    datasetId: string;
    collectionType: string;
    collectionId: string;
    collection: Awaited<ReturnType<typeof readCollection>>['data'];
    globalStorage: ReturnType<typeof useGlobalStorage>;
    selectedAnnotationFilterIds: Readable<string[]>;
    sampleSize: ReturnType<typeof useGlobalStorage>['sampleSize'];
};

// Validate UUID format
function isValidUUID(uuid: string): boolean {
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    return uuidRegex.test(uuid);
}

export const load: LayoutLoad = async ({
    params: { dataset_id, collection_type, collection_id }
}: LayoutLoadEvent): Promise<LayoutLoadResult> => {
    // Validate UUID format for dataset_id
    if (!isValidUUID(dataset_id)) {
        throw redirect(307, routeHelpers.toHome());
    }

    // Validate UUID format for collection_id
    if (!isValidUUID(collection_id)) {
        throw redirect(307, routeHelpers.toHome());
    }

    // ensure the collection actually exists
    let collectionData;
    try {
        const { data } = await readCollection({
            path: { collection_id }
        });
        collectionData = data;
    } catch {
        throw redirect(307, routeHelpers.toHome());
    }

    if (!collectionData) {
        throw redirect(307, routeHelpers.toHome());
    }

    // Validate collection_type matches the collection's sample_type
    // Convert both to lowercase for comparison (URL uses lowercase, enum uses uppercase)
    if (collectionData.sample_type.toLowerCase() !== collection_type.toLowerCase()) {
        // Redirect to correct route with proper collection_type (use lowercase from URL format)
        throw redirect(307, routeHelpers.toCollectionHome(
            dataset_id,
            collectionData.sample_type.toLowerCase(),
            collection_id
        ));
    }

    // Validate dataset_id exists as a root collection
    let datasetCollection;
    try {
        const { data: datasetData } = await readCollection({
            path: { collection_id: dataset_id }
        });
        datasetCollection = datasetData;
    } catch {
        // dataset_id doesn't exist, redirect to home
        throw redirect(307, routeHelpers.toHome());
    }

    // Check if dataset_id is actually a root collection (has no parent)
    if (!datasetCollection || datasetCollection.parent_collection_id !== null) {
        // dataset_id is not a root collection, redirect to home
        throw redirect(307, routeHelpers.toHome());
    }

    // Validate dataset_id matches root collection of the collection_id
    let rootCollection;
    try {
        const { data: rootData } = await readDataset({
            path: { collection_id }
        });
        rootCollection = rootData;
    } catch {
        throw redirect(307, routeHelpers.toHome());
    }

    if (!rootCollection) {
        // rootCollection is null, redirect to home
        throw redirect(307, routeHelpers.toHome());
    }

    if (rootCollection.collection_id !== dataset_id) {
        // Redirect to correct route with proper dataset_id
        throw redirect(307, routeHelpers.toCollectionHome(
            rootCollection.collection_id,
            collection_type,
            collection_id
        ));
    }

    const globalStorage = useGlobalStorage();

    // Convert Set<string> to string[] for backward compatibility with child components
    const selectedAnnotationFilterIdsArray = derived(
        globalStorage.selectedAnnotationFilterIds,
        ($selectedSet) => Array.from($selectedSet)
    );

    return {
        datasetId: dataset_id,
        collectionType: collection_type,
        collectionId: collection_id,
        collection: collectionData,
        globalStorage,
        selectedAnnotationFilterIds: selectedAnnotationFilterIdsArray,
        sampleSize: globalStorage.sampleSize
    };
};
