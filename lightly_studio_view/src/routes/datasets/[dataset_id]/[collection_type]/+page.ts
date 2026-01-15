import { redirect } from '@sveltejs/kit';
import { routeHelpers } from '$lib/routes';
import type { PageLoad } from './$types';

// Validate UUID format
function isValidUUID(uuid: string): boolean {
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    return uuidRegex.test(uuid);
}

export const load: PageLoad = async ({ params }) => {
    const { dataset_id, collection_type } = params;

    // If dataset_id is invalid, redirect to home
    if (!isValidUUID(dataset_id)) {
        throw redirect(307, routeHelpers.toHome());
    }

    // If we reach here, the URL is incomplete (missing collection_id), redirect to home
    throw redirect(307, routeHelpers.toHome());
};
