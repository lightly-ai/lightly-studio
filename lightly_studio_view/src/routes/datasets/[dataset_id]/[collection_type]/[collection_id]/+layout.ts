import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import type { LayoutLoad, LayoutLoadEvent } from './$types';
import { readCollection, readCollectionHierarchy } from '$lib/api/lightly_studio_local/sdk.gen';
import { routeHelpers } from '$lib/routes';
import { redirect, error } from '@sveltejs/kit';
import { derived, type Readable } from 'svelte/store';
import { validate as validateUUID } from 'uuid';
import type { CollectionViewWithCount, CollectionView } from '$lib/api/lightly_studio_local';

export type LayoutLoadResult = {
    collection: CollectionViewWithCount;
    globalStorage: ReturnType<typeof useGlobalStorage>;
    selectedAnnotationFilterIds: Readable<string[]>;
    sampleSize: ReturnType<typeof useGlobalStorage>['sampleSize'];
};

export const load: LayoutLoad = async ({
    params: { dataset_id, collection_type, collection_id }
}: LayoutLoadEvent): Promise<LayoutLoadResult> => {
    // Validate UUID format for dataset_id
    if (!validateUUID(dataset_id)) {
        throw redirect(307, routeHelpers.toHome());
    }

    // Validate UUID format for collection_id
    if (!validateUUID(collection_id)) {
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
        throw redirect(
            307,
            routeHelpers.toCollectionHome(
                dataset_id,
                collectionData.sample_type.toLowerCase(),
                collection_id
            )
        );
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

    if (!datasetCollection) {
        throw redirect(307, routeHelpers.toHome());
    }
    // Check if dataset_id is actually a root collection (has no parent)
    if (datasetCollection.parent_collection_id !== null) {
        throw redirect(307, routeHelpers.toHome());
    }

    // Validate that collection_id belongs to this dataset by checking the hierarchy
    // If collection_id is the dataset_id itself, it's valid
    if (collection_id !== dataset_id) {
        // Fetch the full hierarchy starting from the dataset
        // readCollectionHierarchy returns a flat list of all collections in the hierarchy
        let hierarchy: CollectionView[];
        try {
            const { data: hierarchyData } = await readCollectionHierarchy({
                path: { collection_id: dataset_id }
            });
            hierarchy = hierarchyData || [];
        } catch (err) {
            if (err && typeof err === 'object' && 'status' in err) {
                // Already an error response, re-throw it
                throw err;
            }
            const errorMessage = err instanceof Error ? err.message : String(err);
            throw error(500, `Error loading collection hierarchy: ${errorMessage}`);
        }

        // Check if collection_id exists in the flat hierarchy list
        const collectionExists = hierarchy.some(
            (collection) => collection.collection_id === collection_id
        );

        if (!collectionExists) {
            throw error(
                500,
                `Collection ${collection_id} does not belong to dataset ${dataset_id}`
            );
        }
    }

    const globalStorage = useGlobalStorage();

    // Convert Set<string> to string[] for backward compatibility with child components
    const selectedAnnotationFilterIdsArray = derived(
        globalStorage.selectedAnnotationFilterIds,
        ($selectedSet) => Array.from($selectedSet)
    );

    return {
        collection: collectionData,
        globalStorage,
        selectedAnnotationFilterIds: selectedAnnotationFilterIdsArray,
        sampleSize: globalStorage.sampleSize
    };
};
