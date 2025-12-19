import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import type { LayoutLoad, LayoutLoadEvent } from './$types';
import { readCollection } from '$lib/api/lightly_studio_local/sdk.gen';
import { routeHelpers } from '$lib/routes';
import { redirect } from '@sveltejs/kit';
import { derived, type Readable } from 'svelte/store';

export type LayoutLoadResult = {
    collectionId: string;
    collection: Awaited<ReturnType<typeof readCollection>>['data'];
    globalStorage: ReturnType<typeof useGlobalStorage>;
    selectedAnnotationFilterIds: Readable<string[]>;
    sampleSize: ReturnType<typeof useGlobalStorage>['sampleSize'];
};

export const load: LayoutLoad = async ({
    params: { collection_id }
}: LayoutLoadEvent): Promise<LayoutLoadResult> => {
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

    const globalStorage = useGlobalStorage();

    // Convert Set<string> to string[] for backward compatibility with child components
    const selectedAnnotationFilterIdsArray = derived(
        globalStorage.selectedAnnotationFilterIds,
        ($selectedSet) => Array.from($selectedSet)
    );

    return {
        collectionId: collection_id,
        collection: collectionData,
        globalStorage,
        selectedAnnotationFilterIds: selectedAnnotationFilterIdsArray,
        sampleSize: globalStorage.sampleSize
    };
};
