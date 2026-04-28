import { goto } from '$app/navigation';
import { readCollection } from '$lib/api/lightly_studio_local/sdk.gen';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { routeHelpers } from '$lib/routes';
import { validate as validateUUID } from 'uuid';

import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ params: { dataset_id } }) => {
    if (!validateUUID(dataset_id)) {
        goto(routeHelpers.toHome());
        return new Promise(() => {});
    }

    const response = await readCollection({
        path: { collection_id: dataset_id }
    });

    if (response.error || !response.data || response.data.parent_collection_id !== null) {
        goto(routeHelpers.toHome());
        return new Promise(() => {});
    }

    return {
        globalStorage: useGlobalStorage()
    };
};
