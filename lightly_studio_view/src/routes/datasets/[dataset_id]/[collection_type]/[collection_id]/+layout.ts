import { readCollection } from '$lib/api/lightly_studio_local/sdk.gen';
import type { CollectionViewWithCount } from '$lib/api/lightly_studio_local';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { routeHelpers } from '$lib/routes';
import { redirect } from '@sveltejs/kit';
import { derived, type Readable } from 'svelte/store';
import { validate as validateUUID } from 'uuid';
import type { LayoutLoad, LayoutLoadEvent } from './$types';

export type LayoutLoadResult = {
    collection: CollectionViewWithCount;
    globalStorage: ReturnType<typeof useGlobalStorage>;
    selectedAnnotationFilterIds: Readable<string[]>;
    sampleSize: ReturnType<typeof useGlobalStorage>['sampleSize'];
};

export const load: LayoutLoad = async ({
    params: { dataset_id, collection_type, collection_id }
}: LayoutLoadEvent): Promise<LayoutLoadResult> => {
    if (!validateUUID(dataset_id)) {
        throw redirect(307, routeHelpers.toHome());
    }

    if (!validateUUID(collection_id)) {
        throw redirect(307, routeHelpers.toHome());
    }

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

    if (collectionData.sample_type.toLowerCase() !== collection_type.toLowerCase()) {
        throw redirect(
            307,
            routeHelpers.toCollectionHome(
                dataset_id,
                collectionData.sample_type.toLowerCase(),
                collection_id
            )
        );
    }

    const globalStorage = useGlobalStorage();
    globalStorage.setCollection(collectionData);

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
