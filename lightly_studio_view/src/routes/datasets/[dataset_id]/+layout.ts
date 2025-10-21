import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import type { LayoutLoad, LayoutLoadEvent } from './$types';
import { readDataset } from '$lib/api/lightly_studio_local/sdk.gen';
import { routeHelpers } from '$lib/routes';
import { redirect } from '@sveltejs/kit';
import { derived, type Readable } from 'svelte/store';

export type LayoutLoadResult = {
    datasetId: string;
    dataset: Awaited<ReturnType<typeof readDataset>>['data'];
    globalStorage: ReturnType<typeof useGlobalStorage>;
    selectedAnnotationFilterIds: Readable<string[]>;
    sampleSize: ReturnType<typeof useGlobalStorage>['sampleSize'];
};

export const load: LayoutLoad = async ({
    params: { dataset_id }
}: LayoutLoadEvent): Promise<LayoutLoadResult> => {
    // ensure the dataset actually exists
    let datasetData;
    try {
        const { data } = await readDataset({
            path: { dataset_id }
        });
        datasetData = data;
    } catch {
        throw redirect(307, routeHelpers.toHome());
    }

    if (!datasetData) {
        throw redirect(307, routeHelpers.toHome());
    }

    const globalStorage = useGlobalStorage();

    // Convert Set<string> to string[] for backward compatibility with child components
    const selectedAnnotationFilterIdsArray = derived(
        globalStorage.selectedAnnotationFilterIds,
        ($selectedSet) => Array.from($selectedSet)
    );

    return {
        datasetId: dataset_id,
        dataset: datasetData,
        globalStorage,
        selectedAnnotationFilterIds: selectedAnnotationFilterIdsArray,
        sampleSize: globalStorage.sampleSize
    };
};
